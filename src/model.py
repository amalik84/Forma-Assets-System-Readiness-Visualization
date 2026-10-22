"""Load a day's snapshot and build the reference graph: system > asset > references.

Traversal rule (docs/05, decision 2026-10-21, open question 10):
- From an asset, every directly linked item is a reference (meeting items, RFIs and so on included).
- The walk only continues through issues, forms and documents, and from those it only records
  further issues, forms and documents. Other types are shown, never walked through.
- Never walk through another asset or system. Stop at MAX_DEPTH. Loops are handled by a visited set.
"""

import json
from collections import deque

import config

WALK_TYPES = {"issue", "form", "documentlineage", "documentversion"}
STOP_TYPES = {"asset", "system"}

TYPE_LABELS = {
    "issue": "Issue", "form": "Form", "documentlineage": "Document", "documentversion": "Document",
    "activity": "Schedule activity", "task": "Schedule task", "meetingitem": "Meeting item",
    "meeting": "Meeting", "rfi": "RFI", "submittalitem": "Submittal", "photo": "Photo",
    "sheetlineage": "Sheet", "markup": "Markup", "markupdocument": "Markup",
    "markupsheethistory": "Markup", "pco": "Cost item", "budget": "Cost item", "contract": "Cost item",
    "rfq": "Cost item", "costpayment": "Cost item", "package": "Package", "review": "Review",
}


class Snapshot:
    """Everything fetched for one day, indexed by node key ('type:id')."""

    def __init__(self, assets, issues, forms, relationships, documents):
        self.assets = assets["assets"]
        self.systems = assets["systems"]
        self.lifecycle_sets = assets.get("lifecycleSets", {})
        self.issues = {f"issue:{i['id']}": i for i in issues["issues"]}
        self.forms = {f"form:{f['id']}": f for f in forms["forms"]}
        self.documents = {d["id"]: d for d in documents["documents"]}
        self.edges = relationships["edges"] + documents.get("pinEdges", [])
        self.data_management = documents.get("dataManagement")

    @classmethod
    def load(cls, day=None):
        folder = config.snapshot_dir(day or config.snapshot_day())

        def read(name):
            path = folder / f"{name}.json"
            if not path.exists():
                raise SystemExit(f"{path} not found. Run py src/fetch/{name}.py first.")
            return json.loads(path.read_text(encoding="utf-8"))

        return cls(read("assets"), read("issues"), read("forms"), read("relationships"), read("documents"))

    def node_info(self, key):
        """Display data for one node. 'resolved' is False when the API did not return the item."""
        typ, item_id = key.split(":", 1)
        info = {"key": key, "type": typ, "typeLabel": TYPE_LABELS.get(typ, typ), "resolved": True}
        if typ == "issue":
            i = self.issues.get(key)
            if not i:
                return {**info, "resolved": False, "label": "Issue not returned by the API"}
            return {**info, "label": f"#{i['displayId']} {i['title']}", "status": i["status"],
                    "isDone": i["isDone"], "dueDate": i.get("dueDate"), "itemType": i.get("type")}
        if typ == "form":
            f = self.forms.get(key)
            if not f:
                return {**info, "resolved": False, "label": "Form not returned by the API"}
            return {**info, "label": f"#{f['formNum']} {f['name']}", "status": f["status"],
                    "isDone": f["isDone"], "dueDate": f.get("dueDate"), "itemType": f.get("template"),
                    "templateType": f.get("templateType")}
        if typ in ("documentlineage", "documentversion"):
            d = self.documents.get(key) or {}
            name = d.get("name") or "Document (name not available)"
            if d.get("view"):
                name += f" ({d['view']})"
            if d.get("versionNumber"):
                name += f" v{d['versionNumber']}"
            return {**info, "label": name, "url": d.get("url"), "resolved": bool(d.get("available"))}
        return {**info, "label": TYPE_LABELS.get(typ, typ)}


def build_graph(edges):
    """Undirected adjacency: {node: {neighbour, ...}}."""
    graph = {}
    for e in edges:
        a, b = e["a"], e["b"]
        if a == b:
            continue
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
    return graph


def node_type(key):
    return key.split(":", 1)[0]


def references(start, graph, max_depth):
    """Breadth-first walk from one asset. Returns [{key, depth, path}] with the shortest path per node."""
    found, visited = [], {start}
    queue = deque([(start, [start])])
    while queue:
        node, path = queue.popleft()
        depth = len(path) - 1
        if depth >= max_depth:
            continue
        for nxt in sorted(graph.get(node, ())):
            if nxt in visited:
                continue
            typ = node_type(nxt)
            if typ in STOP_TYPES:
                continue
            if depth > 0 and typ not in WALK_TYPES:
                continue  # beyond the first hop, only issues, forms and documents count
            visited.add(nxt)
            new_path = path + [nxt]
            found.append({"key": nxt, "depth": depth + 1, "path": new_path})
            if typ in WALK_TYPES:
                queue.append((nxt, new_path))
    return found
