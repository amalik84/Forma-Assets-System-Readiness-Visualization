"""Fetch every relationship in the project and save a compact edge list.

All link types are kept (RFIs, meeting items, schedule activities and so on), because the
dashboard shows them as references. Which types the readiness traversal walks through is
decided in step 7 (docs/05), not here.

Usage (from the project folder): py src/fetch/relationships.py
Writes data/raw/<projectId>/YYYY-MM-DD/relationships.json.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow running as a script

import aps_client  # noqa: E402
import config  # noqa: E402
from fetch.common import save  # noqa: E402

PAGE_LIMIT = 100  # the API returns at most 100 per page
MAX_PAGES = 2000  # safety stop, about 200,000 relationships


def fetch_raw():
    """Page through relationships:search with continuationToken."""
    path = f"/bim360/relationship/v2/containers/{config.PROJECT_ID}/relationships:search"
    rels, token = [], None
    for _ in range(MAX_PAGES):
        params = {"pageLimit": PAGE_LIMIT}
        if token:
            params["continuationToken"] = token
        page = aps_client.get_json(path, params)
        batch = page.get("relationships") or []
        rels.extend(batch)
        token = (page.get("page") or {}).get("continuationToken")
        if not token or not batch:
            return rels
    raise RuntimeError(f"More than {MAX_PAGES} pages of relationships, raise MAX_PAGES if this is real.")


def node(entity):
    """Short node key used across the graph: 'type:id', for example 'issue:4f2a...'."""
    return f"{entity['type']}:{entity['id']}"


def normalise(raw_rels):
    edges, seen, skipped_deleted = [], set(), 0
    for r in raw_rels:
        if r.get("isDeleted"):
            skipped_deleted += 1
            continue
        if r["id"] in seen or len(r.get("entities") or []) != 2:
            continue
        seen.add(r["id"])
        a, b = r["entities"]
        edges.append({
            "id": r["id"],
            "a": node(a), "aDomain": a["domain"],
            "b": node(b), "bDomain": b["domain"],
            "createdOn": r.get("createdOn"),
            "source": "relationships",
        })
    return {"edges": edges, "skippedDeleted": skipped_deleted}


def fetch():
    return normalise(fetch_raw())


def main():
    config.require_project()  # fail before any API call
    result = fetch()
    path = save("relationships", result)
    edges = result["edges"]
    pairs = Counter(tuple(sorted((e["a"].split(":")[0], e["b"].split(":")[0]))) for e in edges)
    print(f"Project {config.PROJECT_ID}")
    print(f"Relationships:   {len(edges)}  (deleted skipped: {result['skippedDeleted']})\n")
    print("Most common link types:")
    for (x, y), n in pairs.most_common(12):
        print(f"  {x + ' - ' + y:<35} {n}")
    relevant = {"asset", "issue", "form", "documentlineage", "documentversion"}
    print("\nLinks touching assets:")
    for (x, y), n in pairs.most_common():
        if "asset" in (x, y):
            print(f"  {x + ' - ' + y:<35} {n}")
    print(f"\nLinks between asset/issue/form/document: "
          f"{sum(n for (x, y), n in pairs.items() if x in relevant and y in relevant)}")
    print(f"Saved {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except aps_client.ApiError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
