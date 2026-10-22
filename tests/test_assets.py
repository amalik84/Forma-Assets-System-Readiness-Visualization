"""Unit tests for asset normalisation and system grouping. Run: py -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fetch import assets  # noqa: E402

CATEGORIES = [
    {"id": 1, "name": "ROOT", "isRoot": True, "subcategoryIds": [2]},
    {"id": 2, "name": "Mechanical", "isRoot": False, "subcategoryIds": [3]},
    {"id": 3, "name": "AHU", "isRoot": False, "subcategoryIds": []},
]
STATUSES = [{"id": "s1", "label": "Installed", "color": "green", "statusStepSetId": "set1", "sortOrder": 2},
            {"id": "s0", "label": "Specified", "statusStepSetId": "set1", "sortOrder": 1}]
ATTRS = [{"name": "ca29", "displayName": "System Classification"}]


def asset(aid, system=None, active=True):
    ca = {"ca29": system} if system is not None else {}
    return {"id": aid, "clientAssetId": f"Asset {aid}", "categoryId": "3", "statusId": "s1",
            "isActive": active, "customAttributes": ca}


class SystemGroupingTests(unittest.TestCase):
    def run_normalise(self, raw_assets):
        raw = {"assets": raw_assets, "categories": CATEGORIES, "statuses": STATUSES}
        return assets.normalise(raw, "ca29")

    def test_groups_by_attribute_and_unassigned_last(self):
        result = self.run_normalise([asset("a", "B10"), asset("b", "Supply Air"), asset("c", "B10"), asset("d")])
        names = [s["name"] for s in result["systems"]]
        self.assertEqual(names, ["B10", "Supply Air", assets.NO_SYSTEM])
        self.assertEqual(result["systems"][0]["assetIds"], ["a", "c"])
        self.assertTrue(result["systems"][-1]["isUnassigned"])

    def test_blank_value_counts_as_no_system(self):
        result = self.run_normalise([asset("a", "  ")])
        self.assertEqual(result["assets"][0]["systemIds"], [])
        self.assertEqual(result["systems"][0]["name"], assets.NO_SYSTEM)

    def test_value_is_trimmed(self):
        result = self.run_normalise([asset("a", " B10 "), asset("b", "B10")])
        self.assertEqual(len(result["systems"]), 1)

    def test_inactive_assets_skipped(self):
        result = self.run_normalise([asset("a", "B10"), asset("b", "B10", active=False)])
        self.assertEqual(result["skippedInactive"], 1)
        self.assertEqual(result["systems"][0]["assetIds"], ["a"])

    def test_category_path_and_status_label(self):
        a = self.run_normalise([asset("a", "B10")])["assets"][0]
        self.assertEqual(a["category"], "Mechanical > AHU")
        self.assertEqual(a["status"], "Installed")

    def test_lifecycle_step_in_order(self):
        raw = {"assets": [asset("a", "B10")], "categories": CATEGORIES, "statuses": STATUSES,
               "step_sets": [{"id": "set1", "name": "Default"}]}
        result = assets.normalise(raw, "ca29")
        self.assertEqual(result["lifecycleSets"]["set1"], {"name": "Default", "steps": ["Specified", "Installed"]})
        self.assertEqual(result["assets"][0]["lifecycleStep"], 2)

    def test_group_by_top_level_category(self):
        raw = {"assets": [asset("a"), asset("b", "B10")], "categories": CATEGORIES, "statuses": STATUSES}
        result = assets.normalise(raw, assets.CATEGORY)
        self.assertEqual([s["name"] for s in result["systems"]], ["Mechanical"])
        self.assertEqual(result["systems"][0]["assetIds"], ["a", "b"])

    def test_resolve_attribute_key_case_insensitive(self):
        self.assertEqual(assets.resolve_attribute_key(ATTRS, "system classification"), "ca29")
        with self.assertRaises(SystemExit):
            assets.resolve_attribute_key(ATTRS, "Does Not Exist")


if __name__ == "__main__":
    unittest.main()
