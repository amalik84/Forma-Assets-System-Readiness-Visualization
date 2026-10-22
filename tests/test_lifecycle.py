"""Unit tests for lifecycle phase mapping. Run: py -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import lifecycle  # noqa: E402


class PhaseTests(unittest.TestCase):
    def test_issue_types(self):
        self.assertEqual(lifecycle.phase_of({"type": "issue", "itemType": "Coordination"}), "design")
        self.assertEqual(lifecycle.phase_of({"type": "issue", "itemType": "Commissioning"}), "handover")
        self.assertEqual(lifecycle.phase_of({"type": "issue", "itemType": "Punch List"}), "execution")
        self.assertEqual(lifecycle.phase_of({"type": "issue", "itemType": None}), "execution")

    def test_form_template_types(self):
        self.assertEqual(lifecycle.phase_of({"type": "form", "templateType": "pg.template_type.commissioning"}), "handover")
        self.assertEqual(lifecycle.phase_of({"type": "form", "templateType": "pg.template_type.safety"}), "execution")

    def test_other_types(self):
        self.assertEqual(lifecycle.phase_of({"type": "documentlineage"}), "design")
        self.assertEqual(lifecycle.phase_of({"type": "meetingitem"}), "execution")

    def test_every_phase_id_is_declared(self):
        ids = {p["id"] for p in lifecycle.PHASES}
        used = set(lifecycle.ISSUE_TYPES.values()) | set(lifecycle.FORM_TYPES.values()) | set(lifecycle.OTHER_TYPES.values())
        self.assertTrue(used <= ids)


if __name__ == "__main__":
    unittest.main()
