"""Readiness rules (docs/05): per reference, per asset, per system.

Reference:  blocking  = issue or form that is not done (ISSUE_DONE_STATUSES / FORM_DONE_STATUSES)
            unknown   = issue or form the API did not return (deleted or no access)
            info      = everything else (documents, meeting items, RFIs...), shown but never blocking
Asset:      not_ready if any blocking reference, else unknown if any unknown, else ready
System:     not_ready if any asset not_ready, else unknown if any unknown, else ready
            The '(no system)' bucket gets 'unassigned' and is never counted as ready.

Usage (from the project folder): py src/readiness.py [YYYY-MM-DD]
Reads that day's snapshot, writes data/raw/<projectId>/YYYY-MM-DD/readiness.json, prints a summary.
"""

import json
import sys
from collections import Counter
from datetime import datetime, timezone

import config
import lifecycle
import model

BLOCKING_TYPES = {"issue", "form"}


def classify(info):
    if info["type"] in BLOCKING_TYPES:
        if not info["resolved"]:
            return "unknown"
        return "done" if info.get("isDone") else "blocking"
    return "info"


def worst(statuses):
    statuses = set(statuses)
    if "not_ready" in statuses:
        return "not_ready"
    if "unknown" in statuses:
        return "unknown"
    return "ready"


def assess(snapshot, max_depth):
    graph = model.build_graph(snapshot.edges)
    assets_out = {}
    for a in snapshot.assets:
        refs = []
        for r in model.references(f"asset:{a['id']}", graph, max_depth):
            info = snapshot.node_info(r["key"])
            refs.append({**info, "depth": r["depth"], "state": classify(info),
                         "path": [snapshot.node_info(k)["label"] for k in r["path"][1:]],
                         "pathKeys": r["path"][1:], "phase": lifecycle.phase_of(info)})
        states = Counter(r["state"] for r in refs)
        status = "not_ready" if states["blocking"] else "unknown" if states["unknown"] else "ready"
        # "status" becomes readiness; the asset's own Forma status (Specified, Installed...) moves to assetStatus.
        assets_out[a["id"]] = {**a, "assetStatus": a.get("status"), "status": status, "blockingCount": states["blocking"],
                               "unknownCount": states["unknown"], "references": refs}

    systems_out = []
    for s in snapshot.systems:
        members = [assets_out[i] for i in s["assetIds"] if i in assets_out]
        status = "unassigned" if s["isUnassigned"] else worst(m["status"] for m in members)
        counts = Counter(m["status"] for m in members)
        systems_out.append({**s, "status": status, "assetCount": len(members),
                            "assetsNotReady": counts["not_ready"], "assetsUnknown": counts["unknown"],
                            # 'ready' with no links at all may just mean nobody linked anything yet.
                            "assetsWithReferences": sum(1 for m in members if m["references"]),
                            # Distinct items: one issue linked to five assets counts once.
                            "blockingCount": len({r["key"] for m in members for r in m["references"]
                                                  if r["state"] == "blocking"})})
    return {"systems": systems_out, "assets": list(assets_out.values()),
            "lifecycleSets": snapshot.lifecycle_sets, "phases": lifecycle.PHASES}


def run(day=None):
    day = day or config.snapshot_day()
    snapshot = model.Snapshot.load(day)
    max_depth = int(config.get("MAX_DEPTH") or 2)
    result = assess(snapshot, max_depth)
    result["meta"] = {
        "projectId": config.PROJECT_ID, "snapshotDay": day, "maxDepth": max_depth,
        "issueDoneStatuses": config.get("ISSUE_DONE_STATUSES"), "formDoneStatuses": config.get("FORM_DONE_STATUSES"),
        "systemAttribute": config.SYSTEM_ATTRIBUTE, "dataManagement": snapshot.data_management,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    path = config.snapshot_dir(day) / "readiness.json"
    path.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    return result, path


def main():
    result, path = run(sys.argv[1] if len(sys.argv) > 1 else None)
    meta = result["meta"]
    print(f"Project {meta['projectId']}, snapshot {meta['snapshotDay']}, max depth {meta['maxDepth']}")
    print(f"Done statuses: issues {meta['issueDoneStatuses']}, forms {meta['formDoneStatuses']}\n")
    print(f"{'System':<28}{'Status':<12}{'Assets':>7}{'Linked':>8}{'Not ready':>11}{'Unknown':>9}{'Blocking':>10}")
    for s in result["systems"]:
        print(f"{s['name']:<28}{s['status']:<12}{s['assetCount']:>7}{s['assetsWithReferences']:>8}"
              f"{s['assetsNotReady']:>11}{s['assetsUnknown']:>9}{s['blockingCount']:>10}")
    counts = Counter(a["status"] for a in result["assets"])
    print(f"\nAll assets: {dict(counts)}")
    print(f"Saved {path.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
