"""Fetch assets, categories and statuses, and group assets into systems.

Systems come from an asset custom attribute (SYSTEM_ATTRIBUTE in .env, default
"System Classification"), because there is no public Systems API (docs/04, docs/08 #2).

Usage (from the project folder): py src/fetch/assets.py
Writes data/raw/<projectId>/YYYY-MM-DD/assets.json and prints counts to compare with Forma.
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow running as a script

import aps_client  # noqa: E402
import config  # noqa: E402
from fetch.common import save  # noqa: E402

NO_SYSTEM = "(no system)"
CATEGORY = "category"  # SYSTEM_ATTRIBUTE=category: group by top-level asset category instead
DATACONNECTOR = "dataconnector"  # SYSTEM_ATTRIBUTE=dataconnector: Forma Systems, see fetch/systems_dc.py


def _base():
    return f"/construction/assets/v1/projects/{config.PROJECT_ID}"


def fetch_raw():
    """All raw lookups needed for assets. Each call pages through everything."""
    v2 = f"/construction/assets/v2/projects/{config.PROJECT_ID}"
    return {
        "assets": aps_client.get_all_cursor(f"{v2}/assets", {"includeCustomAttributes": "true"}, limit=200),
        "categories": aps_client.get_json(f"{_base()}/categories", {"limit": 1500})["results"],
        "statuses": aps_client.get_all_offset(f"{_base()}/asset-statuses", limit=100),
        "step_sets": aps_client.get_all_offset(f"{_base()}/status-step-sets", limit=100),
        "custom_attributes": aps_client.get_all_offset(f"{_base()}/custom-attributes", limit=500),
    }


def resolve_attribute_key(custom_attributes, display_name):
    """Map a display name ('System Classification') to its API key ('ca29')."""
    wanted = display_name.strip().lower()
    for attr in custom_attributes:
        if (attr.get("displayName") or "").strip().lower() == wanted:
            return attr["name"]
    names = sorted(a.get("displayName") for a in custom_attributes)
    raise SystemExit(f"SYSTEM_ATTRIBUTE '{display_name}' not found. Available: {names}")


def category_paths(categories):
    """Return {categoryId: 'Parent > Child'} without the technical ROOT node."""
    by_id = {str(c["id"]): c for c in categories}
    parent = {}
    for c in categories:
        for child in c.get("subcategoryIds") or []:
            parent[str(child)] = str(c["id"])

    def path(cid):
        names, seen = [], set()
        while cid in by_id and cid not in seen:
            seen.add(cid)
            if not by_id[cid].get("isRoot"):
                names.append(by_id[cid]["name"])
            cid = parent.get(cid)
        return " > ".join(reversed(names))

    return {cid: path(cid) for cid in by_id}


def lifecycle_sets(statuses, step_sets):
    """{setId: {name, steps: [label, ...]}} in sortOrder: the asset's lifecycle (Specified > ... > Handover)."""
    names = {s["id"]: s.get("name", "") for s in step_sets}
    sets = {}
    for s in sorted(statuses, key=lambda s: s.get("sortOrder") or 0):
        sid = s.get("statusStepSetId")
        if sid:
            sets.setdefault(sid, {"name": names.get(sid, ""), "steps": [], "ids": []})
            sets[sid]["steps"].append(s.get("label", ""))
            sets[sid]["ids"].append(s["id"])
    return sets


def normalise(raw, system_key, asset_system=None):
    """Build the system and asset records described in docs/05."""
    cats = category_paths(raw["categories"])
    statuses = {s["id"]: s for s in raw["statuses"]}
    sets = lifecycle_sets(raw["statuses"], raw.get("step_sets", []))

    assets, skipped_inactive = [], 0
    for a in raw["assets"]:
        if a.get("isActive") is False:
            skipped_inactive += 1
            continue
        category = cats.get(str(a.get("categoryId")), "")
        if system_key == CATEGORY:
            system = category.split(" > ")[0].strip()
        elif system_key == DATACONNECTOR:
            system = (asset_system or {}).get(a["id"], "")
        else:
            system = ((a.get("customAttributes") or {}).get(system_key) or "").strip()
        status = statuses.get(a.get("statusId"), {})
        set_id = status.get("statusStepSetId")
        steps = sets.get(set_id, {}).get("ids", [])
        assets.append({
            "id": a["id"],
            "name": a.get("clientAssetId") or a["id"],
            "barcode": a.get("barcode"),
            "category": category,
            "status": status.get("label", ""),
            "statusColor": status.get("color"),
            # Position in the lifecycle: step 3 of the set's steps (1-based), None if unknown.
            "lifecycleSetId": set_id,
            "lifecycleStep": steps.index(a["statusId"]) + 1 if a.get("statusId") in steps else None,
            "locationId": a.get("locationId"),
            "systemIds": [system] if system else [],
        })
    lifecycle = {sid: {"name": s["name"], "steps": s["steps"]} for sid, s in sets.items()}
    return {"systems": build_systems(assets), "assets": assets, "skippedInactive": skipped_inactive,
            "lifecycleSets": lifecycle}


def build_systems(assets):
    """Group assets by system name. System id = the attribute value itself."""
    members = {}
    for a in assets:
        for sid in a["systemIds"] or [NO_SYSTEM]:
            members.setdefault(sid, []).append(a["id"])
    systems = [{"id": sid, "name": sid, "assetIds": ids, "isUnassigned": sid == NO_SYSTEM}
               for sid, ids in members.items()]
    # Real systems first, alphabetical; the unassigned bucket last.
    return sorted(systems, key=lambda s: (s["isUnassigned"], s["name"].lower()))


def fetch():
    raw = fetch_raw()
    mode = config.SYSTEM_ATTRIBUTE.strip().lower()
    asset_system = None
    if mode == CATEGORY:
        key = CATEGORY
    elif mode == DATACONNECTOR:
        key = DATACONNECTOR
        path = config.snapshot_dir(config.snapshot_day()) / "systems.json"
        if not path.exists():
            raise SystemExit(f"{path} not found. Run py src/fetch/systems_dc.py first (refresh.ps1 does).")
        asset_system = json.loads(path.read_text(encoding="utf-8"))["assetSystem"]
    else:
        key = resolve_attribute_key(raw["custom_attributes"], config.SYSTEM_ATTRIBUTE)
    result = normalise(raw, key, asset_system)
    result["systemAttribute"] = {"displayName": config.SYSTEM_ATTRIBUTE, "key": key}
    return result


def main():
    config.require_project()  # fail before any API call
    result = fetch()
    path = save("assets", result)
    assets, systems = result["assets"], result["systems"]
    attr = result["systemAttribute"]
    assigned = sum(1 for a in assets if a["systemIds"])
    print(f"Project {config.PROJECT_ID}")
    print(f"System attribute: {attr['displayName']} ({attr['key']})\n")
    print(f"Active assets:   {len(assets)}  (inactive skipped: {result['skippedInactive']})")
    print(f"With a system:   {assigned}")
    print(f"Systems:         {sum(1 for s in systems if not s['isUnassigned'])}\n")
    for s in systems:
        print(f"  {s['name']:<30} {len(s['assetIds'])} assets")
    print("\nTop categories:")
    for name, n in Counter(a["category"] for a in assets).most_common(8):
        print(f"  {name or '(none)':<45} {n}")
    print("\nStatuses:")
    for name, n in Counter(a["status"] for a in assets).most_common(8):
        print(f"  {name or '(none)':<45} {n}")
    print(f"\nSaved {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except aps_client.ApiError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
