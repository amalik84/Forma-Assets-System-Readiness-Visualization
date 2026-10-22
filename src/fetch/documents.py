"""Collect the documents that relationships and issue pins point to, and add names from Data Management.

Data Management returns 403 until Document Management access is enabled on the custom integration
(docs/08 #9). Until then documents are kept with their URN only and marked available=False, so the
graph still works and the dashboard can say "name not available".

Usage (from the project folder): py src/fetch/documents.py
Reads today's relationships.json and issues.json, writes documents.json.
"""

import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow running as a script

import aps_client  # noqa: E402
import config  # noqa: E402
from fetch.common import save  # noqa: E402

DOC_TYPES = {"documentlineage", "documentversion"}


def referenced_documents(edges, issues):
    """Return {node_key: type} for every document node in edges plus issue pins."""
    docs = {}
    for e in edges:
        for key in (e["a"], e["b"]):
            typ = key.split(":", 1)[0]
            if typ in DOC_TYPES:
                docs[key] = typ
    for i in issues:
        for urn in i.get("linkedDocumentUrns") or []:
            docs.setdefault(f"documentlineage:{urn}", "documentlineage")
    return docs


def pin_edges(issues):
    """Issue pinned on a document, as edges in the same shape as relationships."""
    return [{"id": f"pin:{i['id']}:{urn}", "a": f"issue:{i['id']}", "aDomain": "autodesk-bim360-issue",
             "b": f"documentlineage:{urn}", "bDomain": "autodesk-bim360-documentmanagement",
             "createdOn": None, "source": "issue.linkedDocuments"}
            for i in issues for urn in i.get("linkedDocumentUrns") or []]


def _lookup(urn):
    """Item details for a lineage URN ('urn:adsk.wipprod:dm.lineage:...')."""
    project = f"b.{config.PROJECT_ID}"
    page = aps_client.get_json(f"/data/v1/projects/{project}/items/{urllib.parse.quote(urn, safe='')}")
    attrs = (page.get("data") or {}).get("attributes") or {}
    links = (page.get("data") or {}).get("links") or {}
    return {"name": attrs.get("displayName") or attrs.get("name"),
            "url": (links.get("webView") or {}).get("href")}


def fetch(edges, issues):
    docs = referenced_documents(edges, issues)
    result, dm_status = [], "ok"
    for key, typ in sorted(docs.items()):
        # Ids can carry a view or a version: 'urn:...:dm.lineage:abc#3D View', '...abc?version=2'.
        urn, _, view = key.split(":", 1)[1].partition("#")
        urn, _, query = urn.partition("?")
        version = urllib.parse.parse_qs(query).get("version", [None])[0]
        doc = {"id": key, "urn": urn, "view": view or None, "type": typ, "name": None,
               "versionNumber": int(version) if version and version.isdigit() else None,
               "url": None, "available": False}
        if dm_status == "ok":
            try:
                doc.update(_lookup(urn), available=True)
            except aps_client.ApiError as e:
                if e.status in (401, 403):
                    dm_status = f"no access ({e.status})"  # same for all documents, stop asking
                elif e.status not in (400, 404):
                    raise  # 404 = deleted, 400 = id format DM does not accept: keep as unavailable
        result.append(doc)
    return {"documents": result, "dataManagement": dm_status, "pinEdges": pin_edges(issues)}


def _load(name, day):
    path = config.snapshot_dir(day) / f"{name}.json"
    if not path.exists():
        raise SystemExit(f"{path} not found. Run py src/fetch/{name}.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    config.require_project()  # fail before any API call
    day = config.snapshot_day()
    edges = _load("relationships", day)["edges"]
    issues = _load("issues", day)["issues"]
    result = fetch(edges, issues)
    path = save("documents", result)
    docs = result["documents"]
    print(f"Project {config.PROJECT_ID}")
    print(f"Documents referenced: {len(docs)}  "
          f"(lineage {sum(d['type'] == 'documentlineage' for d in docs)}, "
          f"version {sum(d['type'] == 'documentversion' for d in docs)})")
    print(f"Issue pins (extra edges): {len(result['pinEdges'])}")
    print(f"Data Management: {result['dataManagement']}, names found for "
          f"{sum(d['available'] for d in docs)} of {len(docs)}")
    print(f"Saved {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except aps_client.ApiError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
