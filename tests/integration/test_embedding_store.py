"""Opt-in embedding storage checks in temporary tables; no model inference."""

from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from rag_workflow_lab.config import EmbeddingSettings, load_database_settings
from rag_workflow_lab.embeddings import ADAPTER_VERSION, MODEL_ID, MODEL_REVISION, EmbeddingResult
from rag_workflow_lab.store import save_chunks, save_embedding_index, save_embeddings, save_snapshots
from scripts.index_corpus import index_corpus


@unittest.skipUnless(os.environ.get("RAG_LAB_TEST_DB") == "1", "Set RAG_LAB_TEST_DB=1 for local DB tests.")
class EmbeddingStoreTests(unittest.TestCase):
    def setUp(self):
        import psycopg

        self.connection = psycopg.connect(
            **load_database_settings().connect_kwargs(), options="-c statement_timeout=5000",
        )
        self.addCleanup(self.connection.close)
        with self.connection.cursor() as cursor:
            for table in ("source_snapshots", "chunks", "embedding_indexes", "chunk_embeddings"):
                cursor.execute(f"CREATE TEMP TABLE {table} (LIKE public.{table} INCLUDING ALL)")
            cursor.execute("ALTER TABLE chunks ADD FOREIGN KEY (snapshot_id) REFERENCES source_snapshots (snapshot_id)")
            cursor.execute("ALTER TABLE chunk_embeddings ADD FOREIGN KEY (index_id) REFERENCES embedding_indexes (index_id)")
            cursor.execute("ALTER TABLE chunk_embeddings ADD FOREIGN KEY (chunk_id) REFERENCES chunks (chunk_id)")
        save_snapshots(self.connection, [{
            "snapshot_id": "snapshot", "source": {"source_id": "fixture", "title": "Fixture", "url": "https://example.org"},
            "sha256": "a" * 64, "downloaded_at": "2026-11-12T00:00:00Z",
        }])
        text = "search_document: SELECT 'quoted';\n  -- Unicode: π"
        save_chunks(self.connection, [{"chunk_id": "chunk", "snapshot_id": "snapshot",
                                      "text": "Fixture", "embedding_text": text, "token_count": 12}])
        self.index = {"index_id": "index", "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                      "dimensions": 768, "chunk_set_sha256": "b" * 64,
                      "settings": {"adapter_version": ADAPTER_VERSION, "device": "cpu"}}
        self.result = EmbeddingResult(
            task="document", model_id=MODEL_ID, model_revision=MODEL_REVISION,
            adapter_version=ADAPTER_VERSION, input_sha256=sha256(text.encode()).hexdigest(),
            token_count=12, vector=(0.6, 0.8) + (0.0,) * 766,
        )
        self.embedder = SimpleNamespace(
            settings=EmbeddingSettings(MODEL_ID, MODEL_REVISION, Path("unused")),
            embed_document=Mock(return_value=self.result),
        )

    def counts(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT (SELECT count(*) FROM embedding_indexes), (SELECT count(*) FROM chunk_embeddings)")
            return cursor.fetchone()

    def test_round_trip_and_repeated_saves_preserve_settings_and_float32_vectors(self):
        for _ in range(2):
            save_embedding_index(self.connection, self.index)
            save_embeddings(self.connection, "index", [("chunk", self.result)])
        self.assertEqual(self.counts(), (1, 1))
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT model_id, model_revision, dimensions, chunk_set_sha256, settings FROM embedding_indexes")
            self.assertEqual(cursor.fetchone(), (MODEL_ID, MODEL_REVISION, 768, "b" * 64, self.index["settings"]))
            cursor.execute("SELECT index_id, chunk_id, input_sha256, embedding::text FROM chunk_embeddings")
            index_id, chunk_id, input_hash, vector = cursor.fetchone()
        self.assertEqual((index_id, chunk_id, input_hash), ("index", "chunk", self.result.input_sha256))
        vector = json.loads(vector)
        self.assertEqual(len(vector), 768)
        for actual, expected in zip(vector, self.result.vector):
            self.assertAlmostEqual(actual, expected, places=7)

    def test_conflicting_index_metadata_is_rejected(self):
        save_embedding_index(self.connection, self.index)
        for key, value in (("model_id", "other/model"), ("model_revision", "c" * 40),
                           ("dimensions", 1024), ("chunk_set_sha256", "c" * 64), ("settings", {"changed": True})):
            with self.subTest(field=key), self.assertRaises(ValueError):
                with self.connection.transaction():
                    save_embedding_index(self.connection, {**self.index, key: value})
        save_embedding_index(self.connection, self.index)
        self.assertEqual(self.counts(), (1, 0))

    def test_missing_chunks_stale_inputs_and_changed_vectors_are_rejected(self):
        save_embedding_index(self.connection, self.index)
        save_embeddings(self.connection, "index", [("chunk", self.result)])
        for chunk_id, result in (("missing", self.result),
                                 ("chunk", replace(self.result, input_sha256="0" * 64)),
                                 ("chunk", replace(self.result, vector=(1.0,) + (0.0,) * 767))):
            with self.subTest(chunk_id=chunk_id), self.assertRaises(ValueError):
                with self.connection.transaction():
                    save_embeddings(self.connection, "index", [(chunk_id, result)])
        save_embeddings(self.connection, "index", [("chunk", self.result)])
        self.assertEqual(self.counts(), (1, 1))

    def test_batch_failure_rolls_back_the_index_and_earlier_vectors(self):
        with self.assertRaises(ValueError):
            with self.connection.transaction():
                save_embedding_index(self.connection, self.index)
                save_embeddings(self.connection, "index", [("chunk", self.result), ("missing", self.result)])
        self.assertEqual(self.counts(), (0, 0))

    def test_separate_indexes_can_store_different_vectors_for_the_same_chunk(self):
        save_embedding_index(self.connection, self.index)
        save_embeddings(self.connection, "index", [("chunk", self.result)])
        save_embedding_index(self.connection, {**self.index, "index_id": "other-index"})
        save_embeddings(self.connection, "other-index", [("chunk", replace(self.result, vector=(1.0,) + (0.0,) * 767))])
        self.assertEqual(self.counts(), (2, 2))

    def test_indexer_uses_stored_inputs_and_reuses_the_same_index(self):
        first = index_corpus(self.connection, self.embedder, {})
        repeated = index_corpus(self.connection, self.embedder, {})
        self.assertEqual(first, repeated)
        self.assertEqual(first["chunks"], 1)
        self.assertEqual(self.counts(), (1, 1))
        text = "search_document: SELECT 'quoted';\n  -- Unicode: π"
        self.assertEqual([call.args[0] for call in self.embedder.embed_document.call_args_list], [text, text])

    def test_indexer_rejects_stale_token_counts_without_saving_an_index(self):
        with self.connection.cursor() as cursor:
            cursor.execute("UPDATE chunks SET token_count = token_count + 1")
        with self.assertRaisesRegex(ValueError, "token count differs"):
            with self.connection.transaction():
                index_corpus(self.connection, self.embedder, {})
        self.assertEqual(self.counts(), (0, 0))

    def test_indexer_requires_a_populated_corpus(self):
        with self.connection.cursor() as cursor:
            cursor.execute("DELETE FROM chunks")
        with self.assertRaisesRegex(ValueError, "No stored chunks"):
            index_corpus(self.connection, self.embedder, {})
        self.embedder.embed_document.assert_not_called()


if __name__ == "__main__":
    unittest.main()
