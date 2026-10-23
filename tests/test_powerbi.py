"""Unit tests for the Power BI export and project generator. Run: py -m unittest discover tests"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import export_powerbi  # noqa: E402
import powerbi_project  # noqa: E402

DATA = {
    "meta": {"projectName": "Demo project A", "snapshotDay": "2026-10-22", "generatedAtLocal": "22 October 2026, 09:25",
             "maxDepth": 2, "issueDoneStatuses": "closed", "formDoneStatuses": "submitted", "systemAttribute": "category"},
    "phases": [{"id": "design", "label": "Design"}, {"id": "execution", "label": "Execution"}],
    "lifecycleSets": {"set1": {"name": "Default", "steps": ["Specified", "Installed"]}},
    "systems": [{"id": "S1", "name": "Tunnel", "status": "not_ready", "isUnassigned": False, "assetCount": 1,
                 "assetsWithReferences": 1, "assetsNotReady": 1, "assetsUnknown": 0, "blockingCount": 1}],
    "assets": [{"id": "A1", "name": "Door [1]", "systemIds": ["S1"], "category": "Tunnel", "barcode": None,
                "assetStatus": "Installed", "status": "not_ready", "blockingCount": 1, "unknownCount": 0, "refCount": 1,
                "lifecycleSetId": "set1", "lifecycleStep": 2, "url": "https://example/asset",
                "references": [{"key": "issue:I1", "typeLabel": "Issue", "label": "#1 Leak", "state": "blocking",
                                "phase": "design", "status": "open", "itemType": "Design", "dueDate": "2026-11-01",
                                "depth": 2, "path": ["model.rvt", "#1 Leak"], "url": "https://example/issue"}]}],
}


class ExportTests(unittest.TestCase):
    def test_tables_flatten_with_keys_that_join(self):
        t = export_powerbi.tables(DATA)
        asset = t["assets"][1][0]
        ref = t["references"][1][0]
        step = t["lifecycle"][1][1]
        self.assertEqual(asset[2], "S1")                       # asset -> system
        self.assertEqual(ref[0], "A1")                         # reference -> asset
        self.assertEqual(asset[12], "set1|2")                  # asset -> lifecycle step
        self.assertEqual(step[0], "set1|2")
        self.assertEqual(step[2], "02 Installed")              # steps sort in order
        self.assertEqual(ref[12], "via model.rvt")             # why linked
        self.assertEqual(ref[6], "Design")                     # phase label

    def test_every_csv_column_is_in_the_model(self):
        t = export_powerbi.tables(DATA)
        for table, (csv_name, columns) in powerbi_project.TABLES.items():
            header = t[csv_name[:-4]][0]
            self.assertEqual([c[0] for c in columns], header, table)


class ProjectTests(unittest.TestCase):
    def test_project_files_and_report_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            pbip = powerbi_project.write_project(tmp, tmp + "\\")
            root = Path(tmp)
            self.assertTrue(pbip.exists())
            report = json.loads((root / f"{powerbi_project.NAME}.Report" / "report.json").read_text(encoding="utf-8"))
            self.assertEqual([s["displayName"] for s in report["sections"]],
                             ["Overview", "Assets and lifecycle", "Blocking items"])
            for s in report["sections"]:
                for v in s["visualContainers"]:
                    json.loads(v["config"])  # every visual config is valid JSON
            tables = root / f"{powerbi_project.NAME}.SemanticModel" / "definition" / "tables"
            self.assertEqual(sorted(p.stem for p in tables.glob("*.tmdl")), sorted(powerbi_project.TABLES))
            self.assertTrue((root / f"{powerbi_project.NAME}.Report" / "StaticResources" / "RegisteredResources"
                             / powerbi_project.CUSTOM_THEME).exists())

    def test_visual_fields_exist_in_model(self):
        names = {t: {c[3].get("name", c[0]) for c in cols} | {m[0] for m in powerbi_project.MEASURES.get(t, [])}
                 for t, (_f, cols) in powerbi_project.TABLES.items()}
        for s in powerbi_project.pages():
            for v in s["visualContainers"]:
                q = json.loads(v["config"])["singleVisual"]["prototypeQuery"]
                alias = {f["Name"]: f["Entity"] for f in q["From"]}
                for sel in q["Select"]:
                    kind = "Measure" if "Measure" in sel else "Column"
                    entity = alias[sel[kind]["Expression"]["SourceRef"]["Source"]]
                    self.assertIn(sel[kind]["Property"], names[entity], f"{s['name']}: {entity}.{sel[kind]['Property']}")


if __name__ == "__main__":
    unittest.main()
