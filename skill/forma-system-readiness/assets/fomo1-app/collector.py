"""Pulls everything FOMO1 needs from Forma (read-only) into one normalized 'raw' dict.

Order: project -> asset reference data -> assets -> issues -> forms -> relationships -> document names.
"""
import logging
import time
import urllib.parse

from aps_client import APSError
from config import S
from readiness import classify, doc_id

log = logging.getLogger("fomo1")


def bare(pid: str) -> str:
    return pid[2:] if pid and pid.startswith("b.") else pid


def _try(label, fn, default):
    try:
        return fn()
    except APSError as e:
        log.warning("%s failed: %s", label, e)
        return default


def project_name(api, hub_id, pid):
    def f():
        j = api.get(f"/project/v1/hubs/{hub_id}/projects/b.{pid}")
        return j["data"]["attributes"]["name"]
    return _try("project name", f, pid)


def fetch_asset_reference(api, pid):
    base = f"/construction/assets/v1/projects/{pid}"
    cats = _try("categories", lambda: {c["id"]: c.get("name", c["id"]) for c in api.iter_items(f"{base}/categories")}, {})
    statuses = _try("asset statuses", lambda: {s["id"]: s.get("label", s["id"]) for s in api.iter_items(f"{base}/asset-statuses", {"limit": 200})}, {})
    attrs = _try("custom attributes", lambda: {a.get("displayName", a.get("name")): a.get("name") for a in api.iter_items(f"{base}/custom-attributes", {"limit": 200})}, {})
    return cats, statuses, attrs


def fetch_assets(api, pid):
    path = f"/construction/assets/v2/projects/{pid}/assets"
    out = []
    for a in api.iter_items(path, {"limit": 200, "includeCustomAttributes": "true"}):
        if a.get("deletedAt") or a.get("isActive") is False:
            continue
        out.append({
            "id": a["id"],
            "name": a.get("clientAssetId") or a.get("description") or a["id"],
            "description": a.get("description"),
            "categoryId": a.get("categoryId"),
            "statusId": a.get("statusId"),
            "locationId": a.get("locationId"),
            "customAttributes": a.get("customAttributes") or {},
            # every other field Forma returns (e.g. a system reference) is kept so `fomo1.py fields` can inspect it
            "extra": {k: v for k, v in a.items() if k not in KNOWN_ASSET_KEYS},
        })
    return out


KNOWN_ASSET_KEYS = {"id", "clientAssetId", "description", "categoryId", "statusId", "locationId",
                    "customAttributes", "deletedAt", "isActive"}


def fetch_system_names(api, pid):
    """Optional: SYSTEMS_ENDPOINT (e.g. /construction/<service>/v1/projects/{projectId}/systems) -> {id: name}."""
    if not S.systems_endpoint:
        return {}
    path = S.systems_endpoint.replace("{projectId}", pid)
    def f():
        names = {}
        for it in api.iter_items(path, {"limit": 200}):
            names[str(it.get("id"))] = it.get("name") or it.get("title") or it.get("displayName") or str(it.get("id"))
        return names
    return _try("systems list", f, {})


def fetch_issues(api, pid):
    base = f"/construction/issues/v1/projects/{pid}"
    types = {}
    for t in _try("issue types", lambda: list(api.iter_items(f"{base}/issue-types", {"include": "subtypes"})), []):
        types[t["id"]] = t.get("title")
        for st in t.get("subtypes") or []:
            types[st["id"]] = f"{t.get('title')} / {st.get('title')}"
    issues = {}
    for i in api.iter_items(f"{base}/issues", {"limit": 100}):
        if i.get("deletedAt") or i.get("deleted"):
            continue
        issues[i["id"]] = {
            "id": i["id"],
            "displayId": i.get("displayId"),
            "title": i.get("title"),
            "status": i.get("status"),
            "dueDate": i.get("dueDate"),
            "assignedTo": i.get("assignedTo"),
            "assignedToType": i.get("assignedToType"),
            "type": types.get(i.get("issueSubtypeId")) or types.get(i.get("issueTypeId")),
            "linkedDocUrns": [d.get("urn") for d in (i.get("linkedDocuments") or []) if d.get("urn")],
        }
    return issues


def fetch_forms(api, pid):
    def norm(f):
        tpl = f.get("formTemplate") or {}
        return {
            "id": f["id"],
            "name": f.get("name") or tpl.get("name") or "Form",
            "status": f.get("status"),
            "formNum": f.get("formNum"),
            "formDate": f.get("formDate"),
            "template": tpl.get("name") or f.get("templateId"),
        }
    try:
        rows = list(api.iter_items(f"/construction/forms/v2/projects/{pid}/forms", {"limit": 200}))
        version = "v2"
    except APSError as e:
        log.info("Forms v2 unavailable (%s) - falling back to v1", e.status)
        rows = _try("forms v1", lambda: list(api.iter_items(f"/construction/forms/v1/projects/{pid}/forms", {"limit": 50})), [])
        version = "v1"
    return {f["id"]: norm(f) for f in rows}, version


def fetch_relationships(api, pid, asset_ids):
    """Pull relationship edges by domain. Falls back to per-asset search if domain-wide search is refused."""
    edges, seen = [], set()

    def add(rel):
        if rel.get("isDeleted") or rel["id"] in seen:
            return
        seen.add(rel["id"])
        ents = rel.get("entities") or []
        if len(ents) == 2:
            edges.append([[e["domain"], e["type"], e["id"]] for e in ents])

    for domain in S.rel_domains:
        try:
            for rel in api.iter_relationships(pid, {"domain": domain}):
                add(rel)
        except APSError as e:
            log.warning("Relationship search for domain %s failed (%s)", domain, e.status)
            if domain == "autodesk-bim360-asset":
                log.info("Falling back to per-asset relationship search (%d assets, slower)", len(asset_ids))
                for aid in asset_ids:
                    for rel in _try(f"rel {aid}", lambda: list(api.iter_relationships(
                            pid, {"domain": domain, "type": "asset", "id": aid})), []):
                        add(rel)
    return edges


def fetch_doc_names(api, pid, urns, cap=800):
    names = {}
    for urn in list(urns)[:cap]:
        item = urllib.parse.quote(urn, safe="")
        def f(item=item):
            j = api.get(f"/data/v1/projects/b.{pid}/items/{item}")
            return j["data"]["attributes"].get("displayName")
        name = _try(f"doc {urn[-12:]}", f, None)
        if name:
            names[urn] = name
    return names


def collect(api):
    if not S.hub_id or not S.project_id:
        raise SystemExit("Set FORMA_HUB_ID and FORMA_PROJECT_ID in .env (see `python fomo1.py hubs` / `projects`).")
    t0 = time.time()
    pid = bare(S.project_id)
    raw = {"meta": {"hubId": S.hub_id, "projectId": pid,
                    "projectName": project_name(api, S.hub_id, pid),
                    "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S")}}
    log.info("Project: %s", raw["meta"]["projectName"])

    raw["categories"], raw["assetStatuses"], raw["attrDefs"] = fetch_asset_reference(api, pid)
    raw["assets"] = fetch_assets(api, pid)
    raw["systemNames"] = fetch_system_names(api, pid)
    log.info("Assets: %d", len(raw["assets"]))
    raw["issues"] = fetch_issues(api, pid)
    log.info("Issues: %d", len(raw["issues"]))
    raw["forms"], raw["meta"]["formsApi"] = fetch_forms(api, pid)
    log.info("Forms: %d (%s)", len(raw["forms"]), raw["meta"]["formsApi"])
    raw["relationships"] = fetch_relationships(api, pid, [a["id"] for a in raw["assets"]])
    log.info("Relationships: %d", len(raw["relationships"]))

    urns = set()
    for a, b in raw["relationships"]:
        for d, t, i in (a, b):
            if classify(d, t) == "document":
                urns.add(doc_id(i))
    for i in raw["issues"].values():
        urns.update(doc_id(u) for u in i["linkedDocUrns"])
    raw["docNames"] = fetch_doc_names(api, pid, urns)
    raw["meta"]["apiCalls"] = api.calls
    raw["meta"]["durationSec"] = round(time.time() - t0, 1)
    return raw
