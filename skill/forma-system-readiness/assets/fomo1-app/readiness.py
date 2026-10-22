"""Readiness engine: turns the raw pull into the dashboard snapshot.

Graph: nodes = assets, issues, forms, documents. Edges = Relationships API links
+ issue pushpins (issue.linkedDocuments). From each asset we walk the graph
(breadth-first, up to MAX_DEPTH hops). Documents and forms are 'pass-through'
nodes; issues are leaves; assets are only followed asset->asset (child equipment).
"""
from collections import defaultdict, deque

from config import S


def classify(domain: str, etype: str) -> str:
    d = (domain or "").lower()
    t = (etype or "").lower()
    if "asset" in d:
        return "asset" if t == "asset" else "other"
    if "issue" in d:
        return "issue"
    if "form" in d or "checklist" in d:
        return "form"
    if "documentmanagement" in d:
        return "document"
    if "rfi" in d:
        return "rfi"
    return "other"


def doc_id(urn: str) -> str:
    """Normalize document version URNs to their lineage/item URN."""
    if not urn:
        return urn
    urn = urn.split("?")[0]
    # version URN  urn:adsk.wipprod:fs.file:vf.ABC  ->  lineage URN  urn:adsk.wipprod:dm.lineage:ABC
    return urn.replace("fs.file:vf.", "dm.lineage:")


def node_key(kind, ident):
    return f"{kind}|{ident}"


def _build_graph(raw):
    adj = defaultdict(set)

    def link(a, b):
        if a != b:
            adj[a].add(b)
            adj[b].add(a)

    for (d1, t1, i1), (d2, t2, i2) in raw["relationships"]:
        k1, k2 = classify(d1, t1), classify(d2, t2)
        if "other" in (k1, k2):
            continue
        i1 = doc_id(i1) if k1 == "document" else i1
        i2 = doc_id(i2) if k2 == "document" else i2
        link(node_key(k1, i1), node_key(k2, i2))
    for iss in raw["issues"].values():
        for urn in iss["linkedDocUrns"]:
            link(node_key("issue", iss["id"]), node_key("document", doc_id(urn)))
    return adj


def _walk(start, adj):
    parent, depth = {start: None}, {start: 0}
    q, found = deque([start]), []
    while q:
        n = q.popleft()
        kind = n.split("|", 1)[0]
        if n != start:
            found.append(n)
        par = parent[n]
        expandable = (
            n == start
            or kind in ("document", "form")
            or (kind == "asset" and S.follow_asset_links and par and par.startswith("asset|"))
        )
        if not expandable or depth[n] >= S.max_depth:
            continue
        for m in sorted(adj.get(n, ())):
            if m not in parent:
                parent[m] = n
                depth[m] = depth[n] + 1
                q.append(m)
    return found, parent


def build_snapshot(raw, history=None):
    pid = raw["meta"]["projectId"]
    assets = {a["id"]: a for a in raw["assets"]}
    issues, forms, docs = raw["issues"], raw["forms"], raw.get("docNames", {})
    cats, stats, attrs = raw.get("categories", {}), raw.get("assetStatuses", {}), raw.get("attrDefs", {})
    adj = _build_graph(raw)
    attr_key = attrs.get(S.system_attribute, S.system_attribute)
    sysmap = load_system_map() if S.group_by == "map_file" else None
    stats_map = {"rows": len(sysmap["rows"]) if sysmap else 0, "matched": 0}

    def url(kind, ident):
        tpl = S.links.get(kind)
        return tpl.format(projectId=pid, id=ident) if tpl else None

    def label(key):
        kind, ident = key.split("|", 1)
        if kind == "asset":
            return assets.get(ident, {}).get("name") or "Asset (not visible)"
        if kind == "issue":
            i = issues.get(ident)
            return f"Issue #{i['displayId']} {i['title']}" if i else "Issue (not visible to you)"
        if kind == "form":
            f = forms.get(ident)
            return f"Form {f.get('formNum') or ''} {f['name']}".replace("  ", " ") if f else "Form (not visible to you)"
        if kind == "document":
            return docs.get(ident) or f"Document …{ident[-8:]}"
        return f"{kind} {ident[-8:]}"

    def ref_for(key, parent):
        kind, ident = key.split("|", 1)
        path, p = [], key
        while p:
            path.append(label(p))
            p = parent[p]
        ref = {"kind": kind, "id": ident, "label": label(key), "path": list(reversed(path)),
               "url": url(kind, ident), "status": None, "state": "ok"}
        if kind == "issue":
            i = issues.get(ident)
            if not i:
                ref["state"] = "unknown"
            else:
                ref.update(status=i["status"], due=i.get("dueDate"), type=i.get("type"),
                           assignee=i.get("assignedTo"))
                if i["status"] in S.issue_closed:
                    ref["state"] = "ok"
                elif i["status"] in S.issue_warning:
                    ref["state"] = "warning"
                else:
                    ref["state"] = "blocking"
        elif kind == "form":
            f = forms.get(ident)
            if not f:
                ref["state"] = "unknown"
            else:
                ref.update(status=f["status"], due=f.get("formDate"), type=f.get("template"))
                ref["state"] = "blocking" if f["status"] in S.form_open else "ok"
        return ref

    out_assets, systems = {}, defaultdict(list)
    linked_issue_ids = set()
    for aid, a in assets.items():
        found, parent = _walk(node_key("asset", aid), adj)
        refs = [ref_for(k, parent) for k in found]
        status_label = stats.get(a.get("statusId"), a.get("statusId"))
        if S.ready_asset_statuses and status_label not in S.ready_asset_statuses:
            refs.insert(0, {"kind": "status", "id": aid, "label": f"Asset status is '{status_label}'",
                            "path": [a["name"]], "state": "blocking", "status": status_label, "url": None})
        for r in refs:
            if r["kind"] == "issue":
                linked_issue_ids.add(r["id"])
        if S.group_by == "map_file":
            system = system_from_map(a, sysmap, stats_map)
        elif S.group_by == "asset_field":
            system = system_from_field(a, raw.get("systemNames", {}))
        elif S.group_by == "category":
            system = cats.get(a.get("categoryId"), "(No category)")
        else:
            system = (a.get("customAttributes") or {}).get(attr_key) or "(No system set)"
        blockers = sum(r["state"] == "blocking" for r in refs)
        warnings = sum(r["state"] in ("warning", "unknown") for r in refs)
        out_assets[aid] = {
            "id": aid, "name": a["name"], "description": a.get("description"),
            "category": cats.get(a.get("categoryId"), ""), "status": status_label,
            "system": str(system), "ready": blockers == 0, "blockers": blockers,
            "warnings": warnings, "url": url("asset", aid), "refs": refs,
        }
        systems[str(system)].append(aid)

    sys_rows = []
    for name, ids in systems.items():
        rows = [out_assets[i] for i in ids]
        open_issues = {r["id"] for a in rows for r in a["refs"] if r["kind"] == "issue" and r["state"] == "blocking"}
        open_forms = {r["id"] for a in rows for r in a["refs"] if r["kind"] == "form" and r["state"] == "blocking"}
        ready_n = sum(a["ready"] for a in rows)
        sys_rows.append({"name": name, "assetIds": sorted(ids, key=lambda i: out_assets[i]["name"]),
                         "assetCount": len(rows), "readyCount": ready_n, "ready": ready_n == len(rows),
                         "openIssues": len(open_issues), "openForms": len(open_forms),
                         "warnings": sum(a["warnings"] for a in rows)})
    sys_rows.sort(key=lambda s: (s["ready"], -s["openIssues"], s["name"]))

    blocking_issues = {r["id"] for a in out_assets.values() for r in a["refs"]
                       if r["kind"] == "issue" and r["state"] == "blocking"}
    blocking_forms = {r["id"] for a in out_assets.values() for r in a["refs"]
                      if r["kind"] == "form" and r["state"] == "blocking"}
    unlinked_open = [i for i in issues.values()
                     if i["id"] not in linked_issue_ids and i["status"] not in S.issue_closed | S.issue_warning]
    summary = {
        "systems": len(sys_rows), "systemsReady": sum(s["ready"] for s in sys_rows),
        "assets": len(out_assets), "assetsReady": sum(a["ready"] for a in out_assets.values()),
        "openIssues": len(blocking_issues), "openForms": len(blocking_forms),
        "unlinkedOpenIssues": len(unlinked_open), "totalIssues": len(issues), "totalForms": len(forms),
    }
    topology = load_topology({r["name"] for r in sys_rows})
    meta = dict(raw["meta"], systemMap=(stats_map if sysmap else None), groupBy=S.group_by, systemField=S.system_field, systemAttribute=S.system_attribute,
                maxDepth=S.max_depth, issueClosed=sorted(S.issue_closed), formOpen=sorted(S.form_open))
    return {"meta": meta, "summary": summary, "systems": sys_rows, "assets": out_assets,
            "topology": topology, "history": history or []}


def load_system_map():
    """CSV with a system column plus any of: id / asset id, name / asset / clientAssetId / asset name, barcode."""
    import csv
    path = S.system_map_file
    if not path.exists():
        raise SystemExit(f"SYSTEM_GROUP_BY=map_file but {path.name} was not found next to fomo1.py. "
                         "Columns: a system column plus an asset id / name / barcode column.")
    text = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text.splitlines()[0], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(text.splitlines(), dialect=dialect))
    if not rows:
        raise SystemExit(f"{path.name} has no rows.")
    cols = {c.strip().lower(): c for c in rows[0].keys() if c}
    pick = lambda *names: next((cols[n] for n in names if n in cols), None)
    sys_col = pick("system", "systems", "system name")
    if not sys_col:
        raise SystemExit(f"{path.name}: no 'System' column. Found: {', '.join(rows[0].keys())}")
    # Forma's "Asset ID" column is the asset's visible name; accept any identifying column and match on all of them
    id_cols = [cols[n] for n in ("id", "guid", "uuid", "asset id", "assetid", "asset_id", "name", "asset", "asset name",
                                 "clientassetid", "client asset id", "barcode", "bar code") if n in cols]
    if not id_cols:
        raise SystemExit(f"{path.name}: no asset identifier column (use e.g. 'Asset ID', 'Name', 'Barcode'). Found: {', '.join(rows[0].keys())}")
    index = {}
    for r in rows:
        v = (r.get(sys_col) or "").strip()
        if not v:
            continue
        for col in id_cols:
            k = (r.get(col) or "").strip().lower()
            if k:
                index.setdefault(k, v)
    return {"rows": rows, "index": index}


def system_from_map(asset, sysmap, stats):
    idx = sysmap["index"]
    for val in (asset["id"], asset.get("name"), asset.get("description"), (asset.get("extra") or {}).get("barcode"),
                (asset.get("extra") or {}).get("clientAssetId")):
        if val and str(val).strip().lower() in idx:
            stats["matched"] += 1
            return idx[str(val).strip().lower()]
    return "(Not in system map)"


def system_from_field(asset, names):
    """Value of asset['extra'][SYSTEM_FIELD_NAME] (also supports a.b paths and lists), mapped to a name if known."""
    val = asset.get("extra") or {}
    for part in S.system_field.split("."):
        if isinstance(val, list):
            val = val[0] if val else None
        val = val.get(part) if isinstance(val, dict) else None
    if isinstance(val, list):
        val = val[0] if val else None
    if isinstance(val, dict):
        val = val.get("name") or val.get("title") or val.get("id")
    if val in (None, ""):
        return "(No system set)"
    return names.get(str(val), str(val))


def load_topology(system_names):
    """Read systems.json: [[upstream, downstream], ...]. Pairs naming unknown systems are reported, not drawn."""
    import json
    topo = {"feeds": [], "unmatched": [], "placeholder": False, "source": None}
    path = S.systems_file
    if not path.exists():
        return topo
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        topo["error"] = f"{path.name} is not valid JSON: {e}"
        return topo
    topo["source"] = path.name
    topo["placeholder"] = bool(cfg.get("placeholder"))
    seen = set()
    for pair in cfg.get("feeds", []):
        if not (isinstance(pair, list) and len(pair) == 2):
            continue
        a, b = str(pair[0]), str(pair[1])
        if a == b or (a, b) in seen:
            continue
        seen.add((a, b))
        if a in system_names and b in system_names:
            topo["feeds"].append([a, b])
        else:
            topo["unmatched"].append([a, b])
    return topo
