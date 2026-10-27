"""Forma Systems (asset > system membership) through the Data Connector API, as lean as possible.

The regular Assets API does not expose Forma Systems; the Data Connector does. To keep it quick:
- one recurring daily Data Connector request with only the "assets" service group, limited to this
  project, is created once and reused (its id is kept in data/dc/<projectId>.json);
- each refresh downloads only two small files from the newest finished job:
  assets_systems.csv and assets_system_memberships.csv. Everything else stays on the live APIs.

Used when SYSTEM_ATTRIBUTE=dataconnector. Needs APS_SCOPES with data:create (to create the request once)
and Data Connector access for the signed-in user (account or project admin).

Usage (from the project folder): py src/fetch/systems_dc.py
Writes data/raw/<projectId>/YYYY-MM-DD/systems.json and keeps the last good result in data/dc/.
"""

import csv
import io
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow running as a script

import aps_client  # noqa: E402
import config  # noqa: E402
from fetch.common import save  # noqa: E402

FILES = ("assets_systems.csv", "assets_system_memberships.csv")
DESCRIPTION = "forma-system-readiness: systems for project {}"
STATE_DIR = config.ROOT / "data" / "dc"


def _base():
    return f"/data-connector/v1/accounts/{config.HUB_ID}"


def _bare(value):
    return (value or "").replace("b.", "")


def _state_path():
    return STATE_DIR / f"{config.PROJECT_ID}.json"


def _load_state():
    p = _state_path()
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save_state(state):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _state_path().write_text(json.dumps(state, indent=1), encoding="utf-8")


# ---------- request and jobs ----------

def create_request(schedule, description):
    """POST one Data Connector request: assets service group only, this project only."""
    now = datetime.now(timezone.utc) + timedelta(minutes=1)  # the API rejects a start in the past
    body = {"description": description, "isActive": True, "scheduleInterval": schedule,
            "effectiveFrom": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "serviceGroups": ["assets"], "projectIdList": [config.PROJECT_ID]}
    if schedule != "ONE_TIME":
        body["reoccuringInterval"] = 1
        body["effectiveTo"] = (now + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    try:
        return aps_client.post_json(f"{_base()}/requests", body)["id"]
    except aps_client.ApiError as e:
        if e.status in (401, 403):
            raise SystemExit(
                f"Data Connector refused to create the request ({e.status}). Check that APS_SCOPES includes "
                "data:create (then run py src\\auth.py login again) and that your Forma role may use the Data Connector.")
        raise


def find_or_create_request(state):
    """Reuse our recurring daily request; find it by description if the state file is gone; create it once otherwise."""
    if state.get("requestId"):
        return state["requestId"]
    wanted = DESCRIPTION.format(config.PROJECT_ID)
    for r in aps_client.get_json(f"{_base()}/requests", {"limit": 100}).get("results", []):
        if r.get("description") == wanted and r.get("isActive") and r.get("scheduleInterval") != "ONE_TIME":
            return r["id"]
    request_id = create_request("DAY", wanted)
    print("  created a daily Data Connector request (assets only, this project)")
    return request_id


def all_jobs(state):
    """Jobs of the daily request plus the one-off start request, newest first."""
    found = []
    for rid in (state.get("requestId"), state.get("startRequestId")):
        if rid:
            found += jobs(rid)
    return sorted(found, key=lambda j: j.get("createdAt") or "", reverse=True)


def jobs(request_id):
    res = aps_client.get_json(f"{_base()}/requests/{request_id}/jobs", {"limit": 20}).get("results", [])
    return sorted(res, key=lambda j: j.get("createdAt") or "", reverse=True)


def is_done(job):
    return (job.get("completionStatus") or "").lower() == "success"


def is_running(job):
    return (job.get("status") or "").lower() not in ("complete", "failed", "cancelled") and not job.get("completionStatus")


def pick_job(job_list, max_age_hours, now=None):
    """Newest successful job, and whether it is fresh enough to use without waiting."""
    now = now or datetime.now(timezone.utc)
    done = [j for j in job_list if is_done(j)]
    if not done:
        return None, False
    newest = done[0]
    completed = _parse_time(newest.get("completedAt"))
    fresh = completed is not None and now - completed <= timedelta(hours=max_age_hours)
    return newest, fresh


def _parse_time(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


# ---------- download ----------

def download(job_id, name):
    """GET data/:name gives a signed URL; the file itself is fetched without our token."""
    info = aps_client.get_json(f"{_base()}/jobs/{job_id}/data/{name}")
    url = info.get("signedUrl") if isinstance(info, dict) else None
    if not url:
        raise SystemExit(f"Data Connector gave no download link for {name}.")
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read().decode("utf-8-sig")


def rows(text):
    return list(csv.DictReader(io.StringIO(text)))


# ---------- systems ----------

def build(systems_rows, membership_rows, project_id):
    """Asset id -> system path ('Parent > Child'), for live systems of this project only."""
    systems = {r["id"]: r["name"].strip() for r in systems_rows
               if _bare(r.get("bim360_project_id")) == project_id and not r.get("deleted_at")}
    parent, asset_system = {}, {}
    for m in membership_rows:
        if _bare(m.get("bim360_project_id")) != project_id or m.get("system_id") not in systems:
            continue
        kind = (m.get("member_type") or "").lower()
        if kind == "system" and m.get("member_id") in systems:
            parent[m["member_id"]] = m["system_id"]
        elif kind == "asset":
            asset_system[m["member_id"]] = m["system_id"]

    def path(sid):
        names, seen = [], set()
        while sid and sid not in seen:
            seen.add(sid)
            names.append(systems[sid])
            sid = parent.get(sid)
        return " > ".join(reversed(names))

    return {"assetSystem": {a: path(s) for a, s in asset_system.items()},
            "systems": sorted(path(s) for s in systems), "nested": len(parent)}


def fetch():
    state = _load_state()
    max_age = float(config.get("DC_MAX_AGE_HOURS") or 26)
    wait_minutes = float(config.get("DC_WAIT_MINUTES") or 20)
    request_id = find_or_create_request(state)
    state["requestId"] = request_id
    _save_state(state)

    deadline = time.time() + wait_minutes * 60
    while True:
        job_list = all_jobs(state)
        job, fresh = pick_job(job_list, max_age)
        if fresh:
            break
        running = any(is_running(j) for j in job_list)
        if not job and not running and not state.get("startRequestId"):
            # The daily request runs on Autodesk's schedule; a one-off request runs now, so the first
            # refresh does not wait a day. Created at most once.
            state["startRequestId"] = create_request("ONE_TIME", DESCRIPTION.format(config.PROJECT_ID) + " (first run)")
            _save_state(state)
            print("  started a one-off Data Connector extract so the first refresh does not wait for the daily run")
            running = True
        if time.time() > deadline or (not running and job):
            break
        print("  waiting for the Data Connector job to finish...")
        time.sleep(30)

    if job and job["id"] == state.get("jobId") and state.get("result"):
        result = state["result"]  # already downloaded this job
    elif job:
        texts = {name: download(job["id"], name) for name in FILES}
        result = build(rows(texts[FILES[0]]), rows(texts[FILES[1]]), config.PROJECT_ID)
        result["extractedAt"] = job.get("completedAt")
        state.update(jobId=job["id"], result=result)
        _save_state(state)
    elif state.get("result"):
        result = state["result"]
        print("  no finished job yet: using the last downloaded systems")
    else:
        raise SystemExit("No Data Connector job has finished yet (the first one can take a while). "
                         "Run .\\refresh.ps1 again later.")
    if job and not fresh:
        print(f"  note: newest systems extract is from {job.get('completedAt')}, older than {max_age:g} hours")
    return result


def main():
    config.require_project()  # fail before any API call
    result = fetch()
    path = save("systems", result)
    print(f"Systems from Forma (Data Connector extract of {result.get('extractedAt')}): "
          f"{len(result['systems'])} systems, {len(result['assetSystem'])} assets in a system, "
          f"{result['nested']} nested systems")
    print(f"Saved {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except aps_client.ApiError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
