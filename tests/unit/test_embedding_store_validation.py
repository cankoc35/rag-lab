"""Embedding storage validation without a driver, database or model."""

from dataclasses import replace
import unittest
from unittest.mock import MagicMock

from rag_workflow_lab.embeddings import ADAPTER_VERSION, MODEL_ID, MODEL_REVISION, EmbeddingResult
from rag_workflow_lab.store import save_embeddings


class EmbeddingStorageValidationTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value.__enter__.return_value
        self.cursor.fetchone.return_value = (MODEL_ID, MODEL_REVISION, 768)
        self.result = EmbeddingResult(
            task="document", model_id=MODEL_ID, model_revision=MODEL_REVISION,
            adapter_version=ADAPTER_VERSION, input_sha256="a" * 64, token_count=12,
            vector=(1.0,) + (0.0,) * 767,
        )

    def test_unknown_index_is_rejected(self):
        self.cursor.fetchone.return_value = None
        with self.assertRaisesRegex(ValueError, "Unknown embedding index"):
            save_embeddings(self.connection, "missing", [("chunk", self.result)])

    def test_mismatched_model_revision_dimensions_and_query_vectors_are_rejected(self):
        for changes in ({"model_id": "other/model"}, {"model_revision": "b" * 40},
                        {"vector": (1.0,) * 767}, {"task": "query"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "mismatch"):
                save_embeddings(self.connection, "index", [("chunk", replace(self.result, **changes))])

    def test_nonfinite_vectors_are_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                result = replace(self.result, vector=(value,) + (0.0,) * 767)
                save_embeddings(self.connection, "index", [("chunk", result)])


if __name__ == "__main__":
    unittest.main()
