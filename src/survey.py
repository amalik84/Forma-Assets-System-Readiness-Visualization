"""Help a new user choose SYSTEM_ATTRIBUTE and VIEWER_MODELS for their project.

Usage (from the project folder):
    py src/survey.py            how could assets be grouped into systems? (reads Forma, a few seconds to minutes)
    py src/survey.py --models   which models could the 3D viewer load? (needs one .\\refresh.ps1 first)

Read only. Prints suggestions; you copy the chosen line into .env yourself.
"""

import json
import re
import sys
from collections import Counter

import aps_client
import config

MODEL_EXTENSIONS = (".rvt", ".nwd", ".nwc", ".ifc", ".dwg", ".dgn")
TOP_MODELS = 10


def survey_systems():
    config.require_project()
    p = config.PROJECT_ID
    base = f"/construction/assets/v1/projects/{p}"
    print(f"Reading assets of project {p} ...")
    attrs = aps_client.get_all_offset(f"{base}/custom-attributes", limit=500)
    assets = aps_client.get_all_cursor(f"/construction/assets/v2/projects/{p}/assets",
                                       {"includeCustomAttributes": "true"}, limit=200)
    cats = aps_client.get_json(f"{base}/categories", {"limit": 1500})["results"]
    total = len(assets)
    if not total:
        print("No assets found. Check Assets access with py src/whoami.py.")
        return

    # Top-level category of each asset (what SYSTEM_ATTRIBUTE=category uses).
    by_id = {str(c["id"]): c for c in cats}
    parent = {str(ch): str(c["id"]) for c in cats for ch in c.get("subcategoryIds") or []}

    def top(cid):
        cid, last = str(cid), None
        while cid in by_id and not by_id[cid].get("isRoot"):
            last, cid = by_id[cid]["name"], parent.get(cid)
        return last

    options = [("category", Counter(top(a.get("categoryId")) for a in assets))]
    for attr in attrs:
        options.append((attr["displayName"], Counter((a.get("customAttributes") or {}).get(attr["name"]) for a in assets)))

    print(f"\n{total} assets. Possible system groupings (a good one is filled on most assets, with about 3 to 50 values):\n")
    print(f"  {'SYSTEM_ATTRIBUTE':<34}{'filled':>12}{'values':>8}   examples")
    rows = []
    for name, counts in options:
        filled = sum(n for v, n in counts.items() if v not in (None, ""))
        values = [v for v in counts if v not in (None, "")]
        if filled:
            rows.append((name, filled, len(values), [v for v, _ in counts.most_common(4) if v not in (None, "")][:3]))
    rows.sort(key=lambda r: (-(r[1] / total >= 0.5 and 2 <= r[2] <= 50), -r[1]))
    for name, filled, n_values, examples in rows[:15]:
        good = "  <- good candidate" if filled / total >= 0.5 and 2 <= n_values <= 50 else ""
        print(f"  {name:<34}{filled:>6} ({filled * 100 // total:>3}%){n_values:>8}   {', '.join(map(str, examples))[:50]}{good}")
    print("\nCopy your choice into .env, for example:  SYSTEM_ATTRIBUTE=category")
    print("Agree with the team which grouping really means 'system'. Category is often only a stopgap.")


def survey_models():
    day_dir = config.snapshot_dir(config.snapshot_day())
    try:
        docs = json.loads((day_dir / "documents.json").read_text(encoding="utf-8"))
        edges = json.loads((day_dir / "relationships.json").read_text(encoding="utf-8"))["edges"]
        assets = json.loads((day_dir / "assets.json").read_text(encoding="utf-8"))["assets"]
    except FileNotFoundError:
        raise SystemExit(f"No snapshot for today in {day_dir}. Run .\\refresh.ps1 first.")

    by_key = {d["id"]: d for d in docs["documents"]}
    counts = Counter()
    for e in edges + docs.get("pinEdges", []):
        for k in (e["a"], e["b"]):
            d = by_key.get(k)
            if d and (d.get("name") or "").lower().endswith(MODEL_EXTENSIONS):
                counts[(d["name"], d["urn"])] += 1
    if not counts:
        print("No models are linked to issues or assets in this project, so there is nothing to suggest.")
        return

    # Asset names that can match a model element: they end in [element id] or [handle].
    matchable = Counter()
    for a in assets:
        if re.search(r"\[[0-9A-Fa-f]+\]\s*$", a["name"]):
            matchable[(a["systemIds"] or ["(no system)"])[0]] += 1
    print("Assets whose names can be matched to model elements, per system:")
    for system, n in matchable.most_common():
        print(f"  {system:<30} {n}")
    if not matchable:
        print("  none: asset names do not carry element ids, so the viewer cannot highlight them by name.")

    from fetch import models  # noqa: E402  (imports config.require_project via common)
    print(f"\nMost-linked models (checking whether each can be viewed):\n")
    viewable = []
    for (name, urn), n in counts.most_common(TOP_MODELS):
        try:
            m = models.resolve(urn)
            status = m["status"]
        except aps_client.ApiError as e:
            status = f"error {e.status}"
        print(f"  {n:>4} links  {name[:45]:<45} {status}")
        if status == "success":
            viewable.append(urn)
    if viewable:
        print("\nStart with the viewable ones, then keep only those that contain your assets:")
        print("  VIEWER_MODELS=" + ",".join(viewable))
        print("\nAfter .\\refresh.ps1 and .\\serve.ps1, select a system: the line under the viewer says")
        print("'N of M assets found in the models'. Remove models that find none (GETTING_STARTED.md, step 7).")


if __name__ == "__main__":
    try:
        survey_models() if "--models" in sys.argv else survey_systems()
    except aps_client.ApiError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
