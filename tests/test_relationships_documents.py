"""Unit tests for relationship edges and document collection. Run: py -m unittest discover tests"""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import aps_client  # noqa: E402
from fetch import documents, relationships  # noqa: E402


def rel(rid, a, b, deleted=False):
    return {"id": rid, "isDeleted": deleted, "createdOn": "2026-01-01",
            "entities": [{"domain": "d1", "type": a[0], "id": a[1]}, {"domain": "d2", "type": b[0], "id": b[1]}]}


class RelationshipTests(unittest.TestCase):
    def test_edges_skip_deleted_and_duplicates(self):
        raw = [rel("r1", ("asset", "A"), ("issue", "I")), rel("r1", ("asset", "A"), ("issue", "I")),
               rel("r2", ("asset", "A"), ("form", "F"), deleted=True)]
        result = relationships.normalise(raw)
        self.assertEqual(len(result["edges"]), 1)
        self.assertEqual(result["skippedDeleted"], 1)
        self.assertEqual((result["edges"][0]["a"], result["edges"][0]["b"]), ("asset:A", "issue:I"))


class DocumentTests(unittest.TestCase):
    EDGES = [{"a": "asset:A", "b": "documentlineage:urn:L1"}, {"a": "issue:I", "b": "documentversion:urn:V1"}]
    ISSUES = [{"id": "I", "linkedDocumentUrns": ["urn:L1", "urn:L2"]}]

    def test_collects_from_edges_and_pins(self):
        docs = documents.referenced_documents(self.EDGES, self.ISSUES)
        self.assertEqual(set(docs), {"documentlineage:urn:L1", "documentversion:urn:V1", "documentlineage:urn:L2"})

    def test_pin_edges(self):
        pins = documents.pin_edges(self.ISSUES)
        self.assertEqual([p["b"] for p in pins], ["documentlineage:urn:L1", "documentlineage:urn:L2"])
        self.assertEqual(pins[0]["source"], "issue.linkedDocuments")

    def test_403_marks_all_unavailable_and_stops_calling(self):
        calls = []

        def deny(urn):
            calls.append(urn)
            raise aps_client.ApiError(403, "x")

        with mock.patch.object(documents, "_lookup", deny):
            result = documents.fetch(self.EDGES, self.ISSUES)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["dataManagement"], "no access (403)")
        self.assertFalse(any(d["available"] for d in result["documents"]))

    def test_view_suffix_stripped_for_lookup(self):
        seen = []

        def lookup(urn):
            seen.append(urn)
            return {"name": "doc", "url": None}

        edges = [{"a": "asset:A", "b": "documentlineage:urn:L1#3D View"}]
        with mock.patch.object(documents, "_lookup", lookup):
            doc = documents.fetch(edges, [])["documents"][0]
        self.assertEqual(seen, ["urn:L1"])
        self.assertEqual((doc["id"], doc["view"]), ("documentlineage:urn:L1#3D View", "3D View"))

    def test_version_query_parsed(self):
        seen = []
        edges = [{"a": "issue:I", "b": "documentversion:urn:L9?version=3"}]
        with mock.patch.object(documents, "_lookup", lambda urn: seen.append(urn) or {"name": "d", "url": None}):
            doc = documents.fetch(edges, [])["documents"][0]
        self.assertEqual(seen, ["urn:L9"])
        self.assertEqual(doc["versionNumber"], 3)

    def test_404_keeps_going(self):
        def lookup(urn):
            if urn == "urn:L1":
                raise aps_client.ApiError(404, "x")
            return {"name": f"doc {urn}", "url": "https://example"}

        with mock.patch.object(documents, "_lookup", lookup):
            result = documents.fetch(self.EDGES, self.ISSUES)
        self.assertEqual(sum(d["available"] for d in result["documents"]), 2)


if __name__ == "__main__":
    unittest.main()
