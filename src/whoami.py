"""Show who is signed in, which hubs and projects they can see, and check the .env IDs.

Usage: py src/whoami.py
"""

import sys

import aps_client
import auth
import config


def main():
    user = aps_client.get_json(config.USERINFO_URL)
    print(f"Signed in as: {user.get('name')} <{user.get('email')}>\n")

    hubs_page = aps_client.get_json("/project/v1/hubs")
    hubs = hubs_page.get("data", [])
    print(f"Hubs ({len(hubs)}):")
    if not hubs:
        # Data Management reports per-region access problems as warnings, not errors.
        for w in (hubs_page.get("meta") or {}).get("warnings", []):
            if w.get("HttpStatusCode") == "403":
                print(f"  {w.get('Title')} {w.get('Detail')}")
        print("  A 403 here usually means this client ID is not added under Custom Integrations "
              "in the account's Account Admin, or the APS app has no ACC/BIM 360 API access.")
    hub_found = False
    for hub in hubs:
        hub_id = hub["id"]
        marker = ""
        if hub_id.removeprefix("b.") == config.HUB_ID:
            hub_found, marker = True, "   <- FORMA_HUB_ID"
        region = hub["attributes"].get("region", "")
        print(f"  {hub['attributes'].get('name')}  [{hub_id}] {region}{marker}")

    if not config.HUB_ID:
        print("\nFORMA_HUB_ID is empty. Copy a hub ID (without 'b.') into .env and run again.")
        return 1
    if not hub_found:
        print(f"\nFORMA_HUB_ID {config.HUB_ID} is not in your hubs (Data Management access).")
        return check_construction_apis()

    projects = aps_client.get_all_jsonapi(f"/project/v1/hubs/b.{config.HUB_ID}/projects")
    print(f"\nProjects in hub ({len(projects)}):")
    project_found = False
    for project in sorted(projects, key=lambda p: p["attributes"].get("name", "").lower()):
        marker = ""
        if project["id"].removeprefix("b.") == config.PROJECT_ID:
            project_found, marker = True, "   <- FORMA_PROJECT_ID"
        print(f"  {project['attributes'].get('name')}  [{project['id']}]{marker}")

    if not project_found:
        print(f"\nFORMA_PROJECT_ID {config.PROJECT_ID} not found in this hub, or you are not a member.")
        return 1
    print("\nOK: hub and project in .env are reachable with your login.")
    return check_construction_apis()


def check_construction_apis():
    """Check the project-level APIs the dashboard needs, independent of Data Management."""
    p = config.PROJECT_ID
    checks = {
        "Assets": f"/construction/assets/v1/projects/{p}/categories",
        "Issues": f"/construction/issues/v1/projects/{p}/users/me",
        "Forms": f"/construction/forms/v1/projects/{p}/form-templates?limit=1",
        "Relationships": f"/bim360/relationship/v2/containers/{p}/relationships:search?pageLimit=1",
        "Data Management": f"/project/v1/hubs/b.{config.HUB_ID}/projects/b.{p}",
    }
    print(f"\nAPI access for project {p}:")
    failed = 0
    for name, path in checks.items():
        try:
            aps_client.get_json(path)
            print(f"  OK    {name}")
        except aps_client.ApiError as e:
            failed += 1
            print(f"  {e.status}   {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (auth.AuthError, aps_client.ApiError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)
