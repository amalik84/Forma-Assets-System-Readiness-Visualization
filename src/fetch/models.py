"""Resolve the models the dashboard viewer loads (VIEWER_MODELS in .env) to their latest viewable version.

VIEWER_MODELS is a comma-separated list of document lineage URNs ('urn:adsk.wipprod:dm.lineage:...').
For each, the latest version is looked up (Data Management 'tip') together with its Model Derivative
URN and translation status. No geometry is downloaded: the browser streams it in the viewer.

Usage (from the project folder): py src/fetch/models.py
Writes data/raw/<projectId>/YYYY-MM-DD/models.json.
"""

import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow running as a script

import aps_client  # noqa: E402
import config  # noqa: E402
from fetch.common import save  # noqa: E402


def configured_urns(value):
    return [u.strip() for u in (value or "").split(",") if u.strip()]


def resolve(lineage_urn):
    project = f"b.{config.PROJECT_ID}"
    tip = aps_client.get_json(f"/data/v1/projects/{project}/items/{urllib.parse.quote(lineage_urn, safe='')}/tip")
    data = tip["data"]
    derivative = (((data.get("relationships") or {}).get("derivatives") or {}).get("data") or {}).get("id")
    model = {"lineageUrn": lineage_urn, "name": data["attributes"].get("displayName") or data["attributes"].get("name"),
             "versionNumber": data["attributes"].get("versionNumber"), "derivativeUrn": derivative,
             "status": "no derivative"}
    if derivative:
        manifest = aps_client.get_json(f"/modelderivative/v2/designdata/{derivative}/manifest")
        model["status"] = manifest.get("status")  # 'success' when the viewer can load it
    return model


def fetch():
    models, errors = [], []
    for urn in configured_urns(config.get("VIEWER_MODELS")):
        try:
            models.append(resolve(urn))
        except aps_client.ApiError as e:
            errors.append({"lineageUrn": urn, "error": e.status})
    return {"models": models, "errors": errors}


def main():
    config.require_project()  # fail before any API call
    result = fetch()
    path = save("models", result)
    for m in result["models"]:
        print(f"  {m['name']:<40} v{m['versionNumber']}  {m['status']}")
    for e in result["errors"]:
        print(f"  ERROR {e['error']} for {e['lineageUrn']}")
    if not result["models"] and not result["errors"]:
        print("VIEWER_MODELS is empty in .env: the dashboard viewer stays off.")
    print(f"Saved {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
