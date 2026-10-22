"""Unit tests for the reference graph and readiness rules. Run: py -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import model  # noqa: E402
import readiness  # noqa: E402


def edge(a, b):
    return {"id": f"{a}-{b}", "a": a, "b": b}


def snapshot(edges, issues=(), forms=(), docs=(), assets=None, systems=None):
    assets = assets or [{"id": "A1", "systemIds": ["S1"]}]
    systems = systems or [{"id": "S1", "name": "S1", "assetIds": [a["id"] for a in assets], "isUnassigned": False}]
    return model.Snapshot(
        {"assets": assets, "systems": systems},
        {"issues": [{"id": i, "displayId": n, "title": i, "status": st, "isDone": st == "closed"}
                    for n, (i, st) in enumerate(issues, 1)]},
        {"forms": [{"id": f, "formNum": n, "name": f, "status": st, "isDone": st == "submitted"}
                   for n, (f, st) in enumerate(forms, 1)]},
        {"edges": list(edges)},
        {"documents": [{"id": d, "name": d, "available": True} for d in docs], "pinEdges": []},
    )


class TraversalTests(unittest.TestCase):
    def test_three_level_chain(self):
        # asset > document > form > issue
        g = model.build_graph([edge("asset:A1", "documentlineage:D1"), edge("documentlineage:D1", "form:F1"),
                               edge("form:F1", "issue:I1")])
        refs = {r["key"]: r for r in model.references("asset:A1", g, max_depth=3)}
        self.assertEqual(refs["issue:I1"]["depth"], 3)
        self.assertEqual(refs["issue:I1"]["path"], ["asset:A1", "documentlineage:D1", "form:F1", "issue:I1"])

    def test_max_depth_stops_walk(self):
        g = model.build_graph([edge("asset:A1", "documentlineage:D1"), edge("documentlineage:D1", "form:F1"),
                               edge("form:F1", "issue:I1")])
        keys = {r["key"] for r in model.references("asset:A1", g, max_depth=2)}
        self.assertEqual(keys, {"documentlineage:D1", "form:F1"})

    def test_loop_terminates_and_each_node_once(self):
        g = model.build_graph([edge("asset:A1", "issue:I1"), edge("issue:I1", "form:F1"),
                               edge("form:F1", "issue:I2"), edge("issue:I2", "issue:I1")])
        refs = model.references("asset:A1", g, max_depth=10)
        self.assertEqual(sorted(r["key"] for r in refs), ["form:F1", "issue:I1", "issue:I2"])

    def test_shortest_path_wins(self):
        g = model.build_graph([edge("asset:A1", "issue:I1"), edge("asset:A1", "form:F1"), edge("form:F1", "issue:I1")])
        refs = {r["key"]: r for r in model.references("asset:A1", g, max_depth=3)}
        self.assertEqual(refs["issue:I1"]["depth"], 1)

    def test_other_types_shown_at_first_hop_but_not_walked(self):
        g = model.build_graph([edge("asset:A1", "meetingitem:M1"), edge("meetingitem:M1", "issue:I1"),
                               edge("asset:A1", "issue:I2"), edge("issue:I2", "rfi:R1")])
        keys = {r["key"] for r in model.references("asset:A1", g, max_depth=3)}
        self.assertEqual(keys, {"meetingitem:M1", "issue:I2"})  # not I1 (behind meeting item), not R1

    def test_does_not_walk_through_other_assets(self):
        g = model.build_graph([edge("asset:A1", "documentlineage:D1"), edge("documentlineage:D1", "asset:A2"),
                               edge("asset:A2", "issue:I9")])
        keys = {r["key"] for r in model.references("asset:A1", g, max_depth=5)}
        self.assertEqual(keys, {"documentlineage:D1"})


class ReadinessTests(unittest.TestCase):
    def test_open_issue_deep_in_chain_blocks_asset_and_system(self):
        snap = snapshot([edge("asset:A1", "documentlineage:D1"), edge("documentlineage:D1", "issue:I1")],
                        issues=[("I1", "open")], docs=["documentlineage:D1"])
        result = readiness.assess(snap, max_depth=3)
        asset, system = result["assets"][0], result["systems"][0]
        self.assertEqual((asset["status"], system["status"]), ("not_ready", "not_ready"))
        blocker = [r for r in asset["references"] if r["state"] == "blocking"][0]
        self.assertEqual(blocker["path"], ["documentlineage:D1", "#1 I1"])

    def test_all_done_is_ready(self):
        snap = snapshot([edge("asset:A1", "issue:I1"), edge("asset:A1", "form:F1")],
                        issues=[("I1", "closed")], forms=[("F1", "submitted")])
        self.assertEqual(readiness.assess(snap, 3)["systems"][0]["status"], "ready")

    def test_unresolved_item_is_unknown_not_ready(self):
        snap = snapshot([edge("asset:A1", "form:MISSING")])
        result = readiness.assess(snap, 3)
        self.assertEqual(result["assets"][0]["status"], "unknown")
        self.assertEqual(result["systems"][0]["status"], "unknown")

    def test_info_references_never_block(self):
        snap = snapshot([edge("asset:A1", "meetingitem:M1"), edge("asset:A1", "rfi:R1")])
        self.assertEqual(readiness.assess(snap, 3)["assets"][0]["status"], "ready")

    def test_unassigned_bucket_and_distinct_blocking_count(self):
        assets = [{"id": "A1", "systemIds": ["S1"]}, {"id": "A2", "systemIds": ["S1"]}, {"id": "A3", "systemIds": []}]
        systems = [{"id": "S1", "name": "S1", "assetIds": ["A1", "A2"], "isUnassigned": False},
                   {"id": "(no system)", "name": "(no system)", "assetIds": ["A3"], "isUnassigned": True}]
        snap = snapshot([edge("asset:A1", "issue:I1"), edge("asset:A2", "issue:I1")],
                        issues=[("I1", "open")], assets=assets, systems=systems)
        s1, unassigned = readiness.assess(snap, 3)["systems"]
        self.assertEqual((s1["assetsNotReady"], s1["blockingCount"], s1["assetsWithReferences"]), (2, 1, 2))
        self.assertEqual(unassigned["status"], "unassigned")


if __name__ == "__main__":
    unittest.main()
