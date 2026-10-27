"""Unit tests for Forma Systems through the Data Connector. Run: py -m unittest discover tests"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fetch import assets, systems_dc  # noqa: E402

P = "proj-1"


def system(sid, name, project=P, deleted=""):
    return {"id": sid, "name": name, "bim360_project_id": project, "deleted_at": deleted}


def member(sid, kind, mid, project=P):
    return {"system_id": sid, "member_type": kind, "member_id": mid, "bim360_project_id": project}


class BuildTests(unittest.TestCase):
    def test_assets_get_their_system_and_nested_paths(self):
        systems = [system("S1", "Substation"), system("S2", "Section 2"), system("S3", "Old", deleted="2026-01-01")]
        members = [member("S1", "asset", "A1"), member("S2", "asset", "A2"), member("S1", "system", "S2"),
                   member("S3", "asset", "A3")]
        r = systems_dc.build(systems, members, P)
        self.assertEqual(r["assetSystem"], {"A1": "Substation", "A2": "Substation > Section 2"})
        self.assertEqual(r["nested"], 1)
        self.assertNotIn("Old", r["systems"])

    def test_other_projects_and_b_prefix(self):
        r = systems_dc.build([system("S1", "X", project="b." + P), system("S9", "Y", project="other")],
                             [member("S1", "asset", "A1", project="b." + P), member("S9", "asset", "A9", project="other")], P)
        self.assertEqual(r["assetSystem"], {"A1": "X"})

    def test_cycle_in_nesting_does_not_hang(self):
        r = systems_dc.build([system("S1", "A"), system("S2", "B")],
                             [member("S1", "system", "S2"), member("S2", "system", "S1"), member("S1", "asset", "X")], P)
        self.assertIn("X", r["assetSystem"])


class JobTests(unittest.TestCase):
    NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)

    def test_newest_successful_job_and_freshness(self):
        jobs = [{"id": "j3", "status": "running", "completionStatus": None, "createdAt": "2026-10-27T11:00:00Z"},
                {"id": "j2", "status": "complete", "completionStatus": "success", "createdAt": "2026-10-26T11:00:00Z",
                 "completedAt": "2026-10-26T11:30:00Z"},
                {"id": "j1", "status": "complete", "completionStatus": "failed", "createdAt": "2026-10-25T11:00:00Z"}]
        job, fresh = systems_dc.pick_job(jobs, 26, self.NOW)
        self.assertEqual((job["id"], fresh), ("j2", True))
        job, fresh = systems_dc.pick_job(jobs, 12, self.NOW)
        self.assertEqual((job["id"], fresh), ("j2", False))
        self.assertTrue(systems_dc.is_running(jobs[0]))
        self.assertFalse(systems_dc.is_running(jobs[1]))

    def test_no_successful_job(self):
        self.assertEqual(systems_dc.pick_job([{"id": "j", "completionStatus": "failed"}], 26, self.NOW), (None, False))


class AssetGroupingTests(unittest.TestCase):
    def test_dataconnector_mode_uses_membership(self):
        raw = {"assets": [{"id": "A1", "clientAssetId": "Pump", "categoryId": "1", "statusId": "s", "isActive": True},
                          {"id": "A2", "clientAssetId": "Valve", "categoryId": "1", "statusId": "s", "isActive": True}],
               "categories": [{"id": 1, "name": "Mech", "isRoot": False, "subcategoryIds": []}],
               "statuses": [{"id": "s", "label": "Installed"}]}
        r = assets.normalise(raw, assets.DATACONNECTOR, {"A1": "Substation > Section 2"})
        names = {s["name"]: s["assetIds"] for s in r["systems"]}
        self.assertEqual(names["Substation > Section 2"], ["A1"])
        self.assertEqual(names[assets.NO_SYSTEM], ["A2"])


if __name__ == "__main__":
    unittest.main()
