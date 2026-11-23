"""Reject invalid search inputs without a driver, database or model."""

import unittest
from unittest.mock import Mock

from rag_workflow_lab.store import search_chunks, search_chunks_full_text


class SearchValidationTests(unittest.TestCase):
    def setUp(self):
        self.connection = Mock()
        self.query = (1.0,) + (0.0,) * 767

    def test_wrong_dimensions_and_zero_vectors_are_rejected(self):
        for vector in ((), self.query[:-1], self.query + (0.0,), (0.0,) * 768):
            with self.subTest(dimensions=len(vector)), self.assertRaises(ValueError):
                search_chunks(self.connection, "index", vector)
        self.connection.cursor.assert_not_called()

    def test_nonfinite_values_are_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                search_chunks(self.connection, "index", (value,) + (0.0,) * 767)
        self.connection.cursor.assert_not_called()

    def test_nonpositive_limits_are_rejected(self):
        for limit in (0, -1):
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, "limit"):
                search_chunks(self.connection, "index", self.query, limit=limit)
        self.connection.cursor.assert_not_called()

    def test_full_text_rejects_nonpositive_limits_before_database_access(self):
        for limit in (0, -1):
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, "limit"):
                search_chunks_full_text(self.connection, "index", "replica lag", limit=limit)
        self.connection.cursor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
