"""Unit tests for issue and form normalisation. Run: py -m unittest discover tests"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fetch import forms, issues  # noqa: E402
from fetch.common import done_statuses  # noqa: E402

TYPES = [{"id": "t1", "title": "Quality", "subtypes": [{"id": "s1", "title": "Snag"}]}]


def issue(iid, status="open", deleted=False, docs=()):
    return {"id": iid, "displayId": 1, "title": f"Issue {iid}", "status": status, "deleted": deleted,
            "issueTypeId": "t1", "issueSubtypeId": "s1",
            "linkedDocuments": [{"urn": u} for u in docs]}


def form(fid, status="draft", template="Checklist"):
    return {"id": fid, "formNum": 4, "name": None, "status": status,
            "formTemplate": {"name": template, "templateType": "pg.template_type.safety"}}


class DoneStatusTests(unittest.TestCase):
    def test_parses_comma_list(self):
        self.assertEqual(done_statuses(" Closed, completed ,"), {"closed", "completed"})
        self.assertEqual(done_statuses(""), set())


class IssueTests(unittest.TestCase):
    def run_normalise(self, raw_issues, done=("closed",)):
        return issues.normalise({"issues": raw_issues, "types": TYPES}, set(done))

    def test_done_flag_follows_setting(self):
        result = self.run_normalise([issue("a", "open"), issue("b", "closed"), issue("c", "in_review")])
        self.assertEqual([i["isDone"] for i in result["issues"]], [False, True, False])

    def test_completed_counts_when_configured(self):
        result = self.run_normalise([issue("a", "completed")], done=("closed", "completed"))
        self.assertTrue(result["issues"][0]["isDone"])

    def test_deleted_issues_skipped(self):
        result = self.run_normalise([issue("a"), issue("b", deleted=True)])
        self.assertEqual(len(result["issues"]), 1)
        self.assertEqual(result["skippedDeleted"], 1)

    def test_type_names_and_linked_documents(self):
        i = self.run_normalise([issue("a", docs=("urn:2", "urn:1", "urn:2"))])["issues"][0]
        self.assertEqual((i["type"], i["subtype"]), ("Quality", "Snag"))
        self.assertEqual(i["linkedDocumentUrns"], ["urn:1", "urn:2"])


class FormTests(unittest.TestCase):
    def test_status_case_insensitive_and_template_name_fallback(self):
        result = forms.normalise({"forms": [form("a", "Submitted"), form("b", "inReview")]}, {"submitted"})
        self.assertEqual([f["isDone"] for f in result["forms"]], [True, False])
        self.assertEqual(result["forms"][0]["name"], "Checklist")
        self.assertEqual(result["forms"][0]["template"], "Checklist")


if __name__ == "__main__":
    unittest.main()
