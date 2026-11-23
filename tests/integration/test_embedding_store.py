"""Opt-in embedding storage/search checks in temporary tables; no inference."""

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
from rag_workflow_lab.retrieval import retrieve, retrieve_hybrid
from rag_workflow_lab.store import get_embedding_index, save_chunks, save_embedding_index, save_embeddings, save_snapshots, search_chunks
from scripts.index_corpus import build_index, index_corpus


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

    def test_search_orders_by_cosine_distance_and_preserves_source_metadata(self):
        chunks = [{
            "chunk_id": name, "snapshot_id": "snapshot", "text": "SELECT 'quoted';\n  -- Unicode: π",
            "embedding_text": f"search_document: {name}", "token_count": 12,
            "heading_path": ["SQL"], "anchors": ["example"],
        } for name in ("z-nearest", "a-farthest")]
        save_chunks(self.connection, chunks)
        save_embedding_index(self.connection, self.index)
        save_embeddings(self.connection, "index", [("chunk", self.result)])
        for chunk, vector in zip(chunks, ((8.0, 0.0), (0.0, 1.0))):
            result = replace(self.result,
                             input_sha256=sha256(chunk["embedding_text"].encode()).hexdigest(),
                             vector=vector + (0.0,) * 766)
            save_embeddings(self.connection, "index", [(chunk["chunk_id"], result)])

        matches = search_chunks(self.connection, "index", (1.0,) + (0.0,) * 767, limit=2)
        self.assertEqual([match["chunk_id"] for match in matches], ["z-nearest", "chunk"])
        self.assertAlmostEqual(matches[0]["distance"], 0.0)
        self.assertAlmostEqual(matches[1]["distance"], 0.4, places=6)
        self.assertEqual(matches[0], {
            "chunk_id": "z-nearest", "snapshot_id": "snapshot", "text": chunks[0]["text"],
            "token_count": 12, "metadata": {"heading_path": ["SQL"], "anchors": ["example"]},
            "source_id": "fixture", "title": "Fixture", "url": "https://example.org", "distance": 0.0,
        })

    def test_search_keeps_indexes_separate_and_returns_no_missing_matches(self):
        save_embedding_index(self.connection, self.index)
        save_embedding_index(self.connection, {**self.index, "index_id": "other-index"})
        query = (1.0,) + (0.0,) * 767
        self.assertEqual(search_chunks(self.connection, "index", query), [])
        save_embeddings(self.connection, "index", [("chunk", self.result)])
        save_embeddings(self.connection, "other-index", [("chunk", replace(self.result, vector=query))])

        matches = search_chunks(self.connection, "index", query)
        self.assertEqual(len(matches), 1)
        self.assertAlmostEqual(matches[0]["distance"], 0.4, places=6)
        self.assertAlmostEqual(search_chunks(self.connection, "other-index", query)[0]["distance"], 0.0)
        self.assertEqual(search_chunks(self.connection, "missing' OR TRUE --", query), [])

    def test_search_does_not_commit_the_callers_transaction(self):
        save_embedding_index(self.connection, self.index)
        save_embeddings(self.connection, "index", [("chunk", self.result)])
        self.assertEqual(len(search_chunks(self.connection, "index", self.result.vector)), 1)
        self.connection.rollback()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('pg_temp.chunk_embeddings')")
            self.assertIsNone(cursor.fetchone()[0])

    def test_retrieval_reads_index_settings_and_searches_the_query_vector(self):
        text = "search_document: SELECT 'quoted';\n  -- Unicode: π"
        index = build_index([("chunk", text, 12)], self.embedder.settings, {})
        save_embedding_index(self.connection, index)
        save_embeddings(self.connection, index["index_id"], [("chunk", self.result)])
        self.assertEqual(get_embedding_index(self.connection, index["index_id"]), index)
        self.embedder.embed_query = Mock(return_value=replace(
            self.result, task="query", vector=(1.0,) + (0.0,) * 767))

        matches = retrieve(self.connection, self.embedder, index["index_id"], "Can replay_lag be NULL?")
        self.embedder.embed_query.assert_called_once_with("Can replay_lag be NULL?")
        self.assertEqual(matches[0]["chunk_id"], "chunk")
        self.assertEqual(matches[0]["source_id"], "fixture")
        self.assertAlmostEqual(matches[0]["distance"], 0.4, places=6)
        with self.assertRaisesRegex(ValueError, "Unknown embedding index"):
            retrieve(self.connection, self.embedder, "missing", "question")
        self.assertEqual(self.embedder.embed_query.call_count, 1)

    def test_indexer_uses_stored_inputs_and_reuses_the_same_index(self):
        first = index_corpus(self.connection, self.embedder, {})
        repeated = index_corpus(self.connection, self.embedder, {})
        self.assertEqual(first, repeated)
        self.assertEqual(first["chunks"], 1)
        self.assertEqual(self.counts(), (1, 1))
        text = "search_document: SELECT 'quoted';\n  -- Unicode: π"
        self.assertEqual([call.args[0] for call in self.embedder.embed_document.call_args_list], [text, text])

    def test_hybrid_merges_live_sql_results_without_reading_another_index(self):
        text = "search_document: Replica lag rule."
        save_chunks(self.connection, [{"chunk_id": "policy", "snapshot_id": "snapshot",
                                      "text": "Replica lag rule.", "embedding_text": text, "token_count": 12}])
        original_text = "search_document: SELECT 'quoted';\n  -- Unicode: π"
        index = build_index([("chunk", original_text, 12), ("policy", text, 12)], self.embedder.settings, {})
        save_embedding_index(self.connection, index)
        save_embeddings(self.connection, index["index_id"], [("chunk", self.result), ("policy", replace(
            self.result, input_sha256=sha256(text.encode()).hexdigest(), vector=(0.0, 1.0) + (0.0,) * 766))])
        save_chunks(self.connection, [{"chunk_id": "unindexed-policy", "snapshot_id": "snapshot",
                                      "text": "Replica lag rule.", "embedding_text": text, "token_count": 12}])
        save_embedding_index(self.connection, self.index)
        save_embeddings(self.connection, "index", [("unindexed-policy", replace(
            self.result, input_sha256=sha256(text.encode()).hexdigest()))])
        self.embedder.embed_query = Mock(return_value=replace(
            self.result, task="query", vector=(1.0,) + (0.0,) * 767))
        matches = retrieve_hybrid(self.connection, self.embedder, index["index_id"], "replica lag", limit=1)
        self.embedder.embed_query.assert_called_once_with("replica lag")
        self.assertEqual([match["chunk_id"] for match in matches], ["policy"])
        self.assertEqual((matches[0]["dense_rank"], matches[0]["full_text_rank"]), (2, 1))
        self.assertAlmostEqual(matches[0]["rrf_score"], 1/62 + 1/61)
        self.assertEqual(matches[0]["source_id"], "fixture")
        self.assertEqual(matches[0]["url"], "https://example.org")

    def test_indexer_selects_sources_and_preserves_other_indexes(self):
        source_id = "other' OR TRUE --"
        text = "search_document: Another source"
        save_snapshots(self.connection, [{
            "snapshot_id": "other-snapshot", "source": {
                "source_id": source_id, "title": "Other", "url": "https://example.org/other"},
            "sha256": "c" * 64, "downloaded_at": "2026-11-18T00:00:00Z",
        }])
        save_chunks(self.connection, [{"chunk_id": "other-chunk", "snapshot_id": "other-snapshot",
                                      "text": "Other", "embedding_text": text, "token_count": 12}])
        self.embedder.embed_document.side_effect = lambda value: replace(
            self.result, input_sha256=sha256(value.encode()).hexdigest())
        original = index_corpus(self.connection, self.embedder, {})
        self.embedder.embed_document.reset_mock()

        selected = index_corpus(self.connection, self.embedder, {}, [source_id, source_id])
        self.embedder.embed_document.assert_called_once_with(text)
        self.assertEqual(selected["chunks"], 1)
        self.assertNotEqual(selected["index_id"], original["index_id"])
        self.assertEqual(get_embedding_index(self.connection, selected["index_id"])["settings"]["source_ids"], [source_id])
        self.assertEqual(index_corpus(self.connection, self.embedder, {}, [source_id]), selected)
        self.assertEqual(self.counts(), (2, 3))
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT chunk_id FROM chunk_embeddings WHERE index_id = %s ORDER BY chunk_id",
                           (original["index_id"],))
            self.assertEqual(cursor.fetchall(), [("chunk",), ("other-chunk",)])

    def test_indexer_rejects_missing_sources_before_embedding(self):
        for source_ids in (["missing"], ["fixture", "missing"]):
            with self.subTest(source_ids=source_ids), self.assertRaisesRegex(ValueError, "No stored chunks for source IDs: missing"):
                index_corpus(self.connection, self.embedder, {}, source_ids)
        self.embedder.embed_document.assert_not_called()
        self.assertEqual(self.counts(), (0, 0))

    def test_indexer_keeps_snapshots_of_the_same_source_separate(self):
        text = "search_document: Revised fixture"
        save_snapshots(self.connection, [{
            "snapshot_id": "revised-snapshot", "source": {
                "source_id": "fixture", "title": "Fixture", "url": "https://example.org"},
            "sha256": "c" * 64, "downloaded_at": "2026-11-23T00:00:00Z",
        }])
        save_chunks(self.connection, [{"chunk_id": "revised-chunk", "snapshot_id": "revised-snapshot",
                                      "text": "Revised", "embedding_text": text, "token_count": 12}])
        self.embedder.embed_document.side_effect = lambda value: replace(
            self.result, input_sha256=sha256(value.encode()).hexdigest())

        indexes = []
        for snapshot_id, expected_text in (("snapshot", "search_document: SELECT 'quoted';\n  -- Unicode: π"),
                                          ("revised-snapshot", text)):
            self.embedder.embed_document.reset_mock()
            selected = index_corpus(self.connection, self.embedder, {}, snapshot_ids=[snapshot_id, snapshot_id])
            self.embedder.embed_document.assert_called_once_with(expected_text)
            self.assertEqual(selected["chunks"], 1)
            self.assertEqual(get_embedding_index(self.connection, selected["index_id"])["settings"]["snapshot_ids"], [snapshot_id])
            self.assertEqual(index_corpus(self.connection, self.embedder, {}, snapshot_ids=[snapshot_id]), selected)
            indexes.append(selected["index_id"])
        self.assertNotEqual(*indexes)
        self.assertEqual(self.counts(), (2, 2))
        for index_id, chunk_id in zip(indexes, ("chunk", "revised-chunk")):
            self.assertEqual([match["chunk_id"] for match in search_chunks(self.connection, index_id, self.result.vector)], [chunk_id])

    def test_indexer_rejects_missing_snapshots_and_mixed_selection_before_embedding(self):
        for snapshot_ids in (["missing' OR TRUE --"], ["snapshot", "missing"]):
            with self.subTest(snapshot_ids=snapshot_ids), self.assertRaisesRegex(ValueError, "No stored chunks for snapshot IDs"):
                index_corpus(self.connection, self.embedder, {}, snapshot_ids=snapshot_ids)
        with self.assertRaisesRegex(ValueError, "not both"):
            index_corpus(self.connection, self.embedder, {}, ["fixture"], snapshot_ids=["snapshot"])
        self.embedder.embed_document.assert_not_called()
        self.assertEqual(self.counts(), (0, 0))

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
