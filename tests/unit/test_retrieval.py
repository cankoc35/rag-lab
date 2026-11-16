"""Query orchestration checks without model packages, drivers or a database."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from rag_workflow_lab.config import EmbeddingSettings
from rag_workflow_lab.embeddings import MODEL_ID, MODEL_REVISION, EmbeddingError
from rag_workflow_lab.retrieval import retrieve
from scripts.index_corpus import build_index


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.connection = Mock()
        settings = EmbeddingSettings(MODEL_ID, MODEL_REVISION, Path("unused"))
        self.vector = (1.0,) + (0.0,) * 767
        self.embedder = SimpleNamespace(settings=settings, embed_query=Mock(
            return_value=SimpleNamespace(vector=self.vector)))
        self.index = build_index([("chunk", "search_document: Fixture", 6)], settings, {})
        self.get_index = self.enterContext(patch("rag_workflow_lab.retrieval.get_embedding_index", return_value=self.index))
        self.search = self.enterContext(patch("rag_workflow_lab.retrieval.search_chunks", return_value=[{"chunk_id": "chunk"}]))

    def test_raw_question_and_its_vector_reach_the_existing_components(self):
        question = "Can replay_lag be NULL?"
        matches = retrieve(self.connection, self.embedder, self.index["index_id"], question, limit=3)
        self.get_index.assert_called_once_with(self.connection, self.index["index_id"])
        self.embedder.embed_query.assert_called_once_with(question)
        self.search.assert_called_once_with(self.connection, self.index["index_id"], self.vector, limit=3)
        self.assertEqual(matches, [{"chunk_id": "chunk"}])

    def test_unknown_index_fails_before_embedding(self):
        self.get_index.side_effect = ValueError("Unknown embedding index")
        with self.assertRaisesRegex(ValueError, "Unknown"):
            retrieve(self.connection, self.embedder, "missing", "question")
        self.embedder.embed_query.assert_not_called()
        self.search.assert_not_called()

    def test_model_revision_and_dimensions_must_match(self):
        for key, value in (("model_id", "other/model"), ("model_revision", "changed"), ("dimensions", 1024)):
            self.get_index.return_value = {**self.index, key: value}
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, "differ"):
                retrieve(self.connection, self.embedder, self.index["index_id"], "question")
        self.embedder.embed_query.assert_not_called()
        self.search.assert_not_called()

    def test_changed_or_missing_embedding_settings_fail_before_embedding(self):
        for key in ("adapter_version", "document_prefix", "query_prefix", "normalization", "device", "dtype", "max_tokens"):
            for value in ("changed", None):
                index = deepcopy(self.index)
                if value is None:
                    del index["settings"][key]
                else:
                    index["settings"][key] = value
                self.get_index.return_value = index
                with self.subTest(field=key, value=value), self.assertRaisesRegex(ValueError, "settings differ"):
                    retrieve(self.connection, self.embedder, self.index["index_id"], "question")
        self.embedder.embed_query.assert_not_called()
        self.search.assert_not_called()

    def test_embedding_failures_do_not_reach_search(self):
        self.embedder.embed_query.side_effect = EmbeddingError("Query input is invalid or too long.")
        with self.assertRaises(EmbeddingError):
            retrieve(self.connection, self.embedder, self.index["index_id"], "")
        self.search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
