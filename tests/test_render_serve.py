"""Unit tests for dashboard data and the local server's host check. Run: py -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import render  # noqa: E402
import serve  # noqa: E402


class HostCheckTests(unittest.TestCase):
    def test_local_hosts_allowed(self):
        self.assertTrue(serve.host_allowed("127.0.0.1:8765", 8765))
        self.assertTrue(serve.host_allowed("localhost:8765", 8765))
        self.assertTrue(serve.host_allowed("localhost", 8765))

    def test_other_hosts_refused(self):
        self.assertFalse(serve.host_allowed("evil.example.com:8765", 8765))   # DNS rebinding
        self.assertFalse(serve.host_allowed("127.0.0.1:9999", 8765))
        self.assertFalse(serve.host_allowed("", 8765))
        self.assertFalse(serve.host_allowed(None, 8765))


class RenderTests(unittest.TestCase):
    def ref(self, key, path_keys, state="blocking"):
        return {"key": key, "typeLabel": "Issue", "label": "x", "state": state, "depth": len(path_keys),
                "path": ["p"] * len(path_keys), "pathKeys": path_keys, "phase": "design", "type": key.split(":")[0],
                "resolved": True}

    def test_via_is_previous_item_on_path(self):
        r = render.slim_reference(self.ref("issue:I1", ["documentlineage:D1", "issue:I1"]))
        self.assertEqual((r["via"], r["phase"], r["key"]), ("documentlineage:D1", "design", "issue:I1"))
        self.assertIsNone(render.slim_reference(self.ref("issue:I2", ["issue:I2"]))["via"])

    def test_only_successful_models_are_passed_to_the_viewer(self):
        readiness = {"assets": [], "systems": [], "meta": {"generatedAt": "2026-10-21T10:00:00+00:00"}}
        models = {"models": [{"name": "A.rvt", "versionNumber": 2, "derivativeUrn": "dXJu", "status": "success"},
                             {"name": "B.rvt", "versionNumber": 1, "derivativeUrn": "dXJv", "status": "inprogress"}]}
        data = render.build_data(readiness, models=models)
        self.assertEqual([m["name"] for m in data["models"]], ["A.rvt"])


if __name__ == "__main__":
    unittest.main()
