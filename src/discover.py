"""Discovery run: pull small samples from each API and save the raw responses.

Usage: py src/discover.py

Writes data/raw/discovery/<name>.json (git-ignored, project data stays on this machine)
and prints a short summary per endpoint: status, top-level keys, item count, paging fields.
Used to verify endpoints and field names in docs/04 before building on them.
"""

import json
from collections import Counter

import aps_client
import config

OUT = config.ROOT / "data" / "raw" / config.PROJECT_ID / "discovery"
P = config.PROJECT_ID
ASSETS_V1 = f"/construction/assets/v1/projects/{P}"
ASSETS_V2 = f"/construction/assets/v2/projects/{P}"
ISSUES = f"/construction/issues/v1/projects/{P}"
FORMS = f"/construction/forms/v1/projects/{P}"
REL = f"/bim360/relationship/v2/containers/{P}"


def save(name, payload):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def items_of(payload):
    if isinstance(payload, list):
        return payload
    for key in ("results", "data", "relationships"):
        if isinstance(payload.get(key), list):
            return payload[key]
    return []


def probe(name, method, path, params=None, body=None):
    """Call one endpoint, save the response, print a summary. Returns the payload or None."""
    try:
        payload = aps_client.request(method, path, params=params, body=body)
    except aps_client.ApiError as e:
        print(f"  {e.status:<5} {name:<28} {e.detail[:90]}")
        save(name, {"_error": e.status, "_detail": e.detail})
        return None
    payload = payload if payload is not None else {}
    save(name, payload)
    items = items_of(payload)
    keys = list(payload.keys()) if isinstance(payload, dict) else ["<list>"]
    paging = payload.get("pagination") or payload.get("page") if isinstance(payload, dict) else None
    print(f"  OK    {name:<28} items={len(items):<4} keys={keys}")
    if paging:
        print(f"        paging: {paging}")
    return payload


def field_values(items, field):
    return dict(Counter(str(i.get(field)) for i in items if isinstance(i, dict)))


def main():
    print(f"Discovery for project {P}, saving to {OUT}\n")

    print("Assets")
    a2 = probe("assets_v2", "GET", f"{ASSETS_V2}/assets", {"limit": 5})
    probe("assets_v1", "GET", f"{ASSETS_V1}/assets", {"limit": 5})
    probe("asset_categories", "GET", f"{ASSETS_V1}/categories")
    probe("asset_statuses", "GET", f"{ASSETS_V1}/asset-statuses")
    probe("asset_status_step_sets", "GET", f"{ASSETS_V1}/status-step-sets")
    probe("asset_custom_attributes", "GET", f"{ASSETS_V1}/custom-attributes")

    print("\nSystems")
    systems = probe("systems_v1", "GET", f"{ASSETS_V1}/systems", {"limit": 5})
    probe("systems_v2", "GET", f"{ASSETS_V2}/systems", {"limit": 5})
    first_system = (items_of(systems) or [{}])[0].get("id") if systems else None
    if first_system:
        # Which endpoint gives the assets in a system? Try the likely shapes and record what works.
        probe("system_one", "GET", f"{ASSETS_V1}/systems/{first_system}")
        probe("system_assets_v1", "GET", f"{ASSETS_V1}/systems/{first_system}/assets", {"limit": 5})
        probe("system_assets_v2", "GET", f"{ASSETS_V2}/systems/{first_system}/assets", {"limit": 5})
        probe("system_memberships", "GET", f"{ASSETS_V1}/systems/{first_system}/system-memberships", {"limit": 5})

    print("\nIssues")
    issues = probe("issues", "GET", f"{ISSUES}/issues", {"limit": 50})
    probe("issue_types", "GET", f"{ISSUES}/issue-types")
    probe("issue_attribute_definitions", "GET", f"{ISSUES}/issue-attribute-definitions")

    print("\nForms")
    forms = probe("forms", "GET", f"{FORMS}/forms", {"limit": 50})
    probe("form_templates", "GET", f"{FORMS}/form-templates", {"limit": 50})

    print("\nRelationships")
    rels = probe("relationships_search", "GET", f"{REL}/relationships:search", {"pageLimit": 200})
    probe("relationships_writable", "GET", "/bim360/relationship/v2/utility/relationships:writable")
    first_asset = (items_of(a2) or [{}])[0].get("id") if a2 else None

    # ---------- summary of what matters for the docs ----------
    print("\nFindings")
    if issues:
        print(f"  issue statuses (sample): {field_values(items_of(issues), 'status')}")
    if forms:
        print(f"  form statuses (sample):  {field_values(items_of(forms), 'status')}")
    if rels:
        pairs = Counter()
        for r in items_of(rels):
            for ent in r.get("entities", []):
                pairs[(ent.get("domain"), ent.get("type"))] += 1
        print("  relationship domain/type pairs:")
        for (domain, typ), n in pairs.most_common():
            print(f"    {domain} / {typ}: {n}")
        if first_asset:
            linked = [r for r in items_of(rels)
                      if any(e.get("id") == first_asset for e in r.get("entities", []))]
            print(f"  relationships touching first sample asset: {len(linked)}")
    print("\nDone. Raw responses are in data/raw/discovery/.")


if __name__ == "__main__":
    main()
