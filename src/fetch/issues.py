"""Fetch all issues and normalise them to the Issue shape in docs/05.

Usage (from the project folder): py src/fetch/issues.py
Writes data/raw/<projectId>/YYYY-MM-DD/issues.json and prints counts to compare with Forma.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow running as a script

import aps_client  # noqa: E402
import config  # noqa: E402
from fetch.common import done_statuses, save  # noqa: E402


def _base():
    return f"/construction/issues/v1/projects/{config.PROJECT_ID}"


def fetch_raw():
    return {
        "issues": aps_client.get_all_offset(f"{_base()}/issues", limit=100),
        "types": aps_client.get_all_offset(f"{_base()}/issue-types", {"include": "subtypes"}, limit=200),
    }


def type_names(types):
    """Return {typeId: title} and {subtypeId: title}."""
    by_type, by_subtype = {}, {}
    for t in types:
        by_type[t["id"]] = t.get("title", "")
        for st in t.get("subtypes") or []:
            by_subtype[st["id"]] = st.get("title", "")
    return by_type, by_subtype


def normalise(raw, done):
    by_type, by_subtype = type_names(raw["types"])
    issues, skipped_deleted = [], 0
    for i in raw["issues"]:
        if i.get("deleted") or i.get("deletedAt"):
            skipped_deleted += 1
            continue
        status = (i.get("status") or "").lower()
        issues.append({
            "id": i["id"],
            "displayId": i.get("displayId"),
            "title": i.get("title") or "",
            "status": status,
            "isDone": status in done,
            "type": by_type.get(i.get("issueTypeId"), ""),
            "subtype": by_subtype.get(i.get("issueSubtypeId"), ""),
            "assignedTo": i.get("assignedTo"),
            "assignedToType": i.get("assignedToType"),
            "dueDate": i.get("dueDate"),
            "locationId": i.get("locationId"),
            "published": i.get("published"),
            # Documents the issue is pinned on: an extra edge source next to Relationships (docs/05).
            "linkedDocumentUrns": sorted({d["urn"] for d in i.get("linkedDocuments") or [] if d.get("urn")}),
            "updatedAt": i.get("updatedAt"),
        })
    return {"issues": issues, "skippedDeleted": skipped_deleted, "doneStatuses": sorted(done)}


def fetch():
    return normalise(fetch_raw(), done_statuses(config.get("ISSUE_DONE_STATUSES") or "closed"))


def main():
    config.require_project()  # fail before any API call
    result = fetch()
    path = save("issues", result)
    issues = result["issues"]
    print(f"Project {config.PROJECT_ID}")
    print(f"Issues:          {len(issues)}  (deleted skipped: {result['skippedDeleted']})")
    print(f"Done statuses:   {result['doneStatuses']}")
    print(f"Open (blocking): {sum(1 for i in issues if not i['isDone'])}\n")
    print("By status:")
    for name, n in Counter(i["status"] for i in issues).most_common():
        print(f"  {name:<20} {n}")
    print("\nBy type:")
    for name, n in Counter(i["type"] for i in issues).most_common(8):
        print(f"  {name or '(none)':<40} {n}")
    print(f"\nPinned on documents: {sum(1 for i in issues if i['linkedDocumentUrns'])}")
    print(f"Saved {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except aps_client.ApiError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
