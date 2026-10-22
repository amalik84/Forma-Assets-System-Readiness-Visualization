"""Fetch all forms and normalise them to the Form shape in docs/05.

Usage (from the project folder): py src/fetch/forms.py
Writes data/raw/<projectId>/YYYY-MM-DD/forms.json and prints counts to compare with Forma.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow running as a script

import aps_client  # noqa: E402
import config  # noqa: E402
from fetch.common import done_statuses, save  # noqa: E402


def fetch_raw():
    path = f"/construction/forms/v1/projects/{config.PROJECT_ID}/forms"
    # Include forms on inactive templates: they can still be linked to assets.
    return {"forms": aps_client.get_all_cursor(path, {"includeInactiveFormTemplates": "true"},
                                               limit=50, results_key="data")}


def normalise(raw, done):
    forms = []
    for f in raw["forms"]:
        status = f.get("status") or ""
        template = f.get("formTemplate") or {}
        forms.append({
            "id": f["id"],
            "formNum": f.get("formNum"),
            "name": f.get("name") or template.get("name") or "",
            "template": template.get("name", ""),
            "templateType": template.get("templateType", ""),
            "status": status,
            "isDone": status.lower() in done,
            "assigneeId": f.get("assigneeId"),
            "assigneeType": f.get("assigneeType"),
            "dueDate": f.get("dueDate"),
            "formDate": f.get("formDate"),
            "locationId": f.get("locationId"),
            "updatedAt": f.get("updatedAt"),
        })
    return {"forms": forms, "doneStatuses": sorted(done)}


def fetch():
    return normalise(fetch_raw(), done_statuses(config.get("FORM_DONE_STATUSES") or "submitted"))


def main():
    config.require_project()  # fail before any API call
    result = fetch()
    path = save("forms", result)
    forms = result["forms"]
    print(f"Project {config.PROJECT_ID}")
    print(f"Forms:           {len(forms)}")
    print(f"Done statuses:   {result['doneStatuses']}")
    print(f"Open (blocking): {sum(1 for f in forms if not f['isDone'])}\n")
    print("By status:")
    for name, n in Counter(f["status"] for f in forms).most_common():
        print(f"  {name:<20} {n}")
    print("\nBy template:")
    for name, n in Counter(f["template"] for f in forms).most_common(8):
        print(f"  {name or '(none)':<45} {n}")
    print(f"\nSaved {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except aps_client.ApiError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
