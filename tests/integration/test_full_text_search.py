"""Opt-in full-text SQL checks with temporary tables; no models or public writes."""

from dataclasses import replace
from hashlib import sha256
import os
import unittest

from rag_workflow_lab.config import load_database_settings
from rag_workflow_lab.embeddings import ADAPTER_VERSION, MODEL_ID, MODEL_REVISION, EmbeddingResult
from rag_workflow_lab.store import save_chunks, save_embedding_index, save_embeddings, save_snapshots, search_chunks_full_text


@unittest.skipUnless(os.environ.get("RAG_LAB_TEST_DB") == "1", "Set RAG_LAB_TEST_DB=1 for local DB tests.")
class FullTextSearchTests(unittest.TestCase):
    def setUp(self):
        import psycopg

        self.connection = psycopg.connect(**load_database_settings().connect_kwargs())
        self.addCleanup(self.connection.close)
        with self.connection.cursor() as cursor:
            for table in ("source_snapshots", "chunks", "embedding_indexes", "chunk_embeddings"):
                cursor.execute(f"CREATE TEMP TABLE {table} (LIKE public.{table} INCLUDING ALL)")
        for snapshot_id in ("v1", "v2"):
            save_snapshots(self.connection, [{
                "snapshot_id": snapshot_id, "source": {"source_id": "policy", "title": "Policy", "url": "https://example.org/policy"},
                "sha256": "a" * 64, "downloaded_at": "2026-11-23T00:00:00Z",
            }])
        chunks = [{"chunk_id": name, "snapshot_id": snapshot, "text": text,
                   "embedding_text": "search_document: " + text, "token_count": 10,
                   "heading_path": ["Policy"], "anchors": ["lag"]}
                  for name, snapshot, text in (
                      ("a", "v1", "Replica lag."), ("b", "v1", "Replica lag."),
                      ("z", "v1", "Replica lag. Replica lag."), ("partial", "v1", "Replica."),
                      ("new", "v2", "Replica lag."), ("unindexed", "v1", "Replica lag."),
                  )]
        save_chunks(self.connection, chunks)
        for index_id, names in (("old-index", {"a", "b", "z", "partial"}), ("new-index", {"new"})):
            save_embedding_index(self.connection, {
                "index_id": index_id, "model_id": MODEL_ID, "model_revision": MODEL_REVISION,
                "dimensions": 768, "chunk_set_sha256": "b" * 64, "settings": {},
            })
            result = EmbeddingResult("document", MODEL_ID, MODEL_REVISION, ADAPTER_VERSION,
                                     "", 10, (1.0,) + (0.0,) * 767)
            save_embeddings(self.connection, index_id, [
                (c["chunk_id"], replace(result, input_sha256=sha256(c["embedding_text"].encode()).hexdigest()))
                for c in chunks if c["chunk_id"] in names
            ])

    def test_english_stemming_or_matching_rank_ties_limit_and_citation_fields(self):
        matches = search_chunks_full_text(self.connection, "old-index", "replicas lags")
        self.assertEqual([m["chunk_id"] for m in matches], ["z", "a", "b", "partial"])
        self.assertGreater(matches[0]["text_score"], matches[1]["text_score"])
        self.assertEqual(matches[1]["text_score"], matches[2]["text_score"])
        self.assertEqual(matches[0]["source_id"], "policy")
        self.assertEqual(matches[0]["snapshot_id"], "v1")
        self.assertEqual(matches[0]["url"], "https://example.org/policy")
        self.assertEqual(matches[0]["metadata"], {"heading_path": ["Policy"], "anchors": ["lag"]})
        self.assertNotIn("distance", matches[0])
        self.assertEqual(search_chunks_full_text(self.connection, "old-index", "replica lag", limit=2), matches[:2])

    def test_versions_of_the_same_source_and_unindexed_chunks_stay_separate(self):
        self.assertEqual([m["chunk_id"] for m in search_chunks_full_text(self.connection, "new-index", "replica lag")], ["new"])
        self.assertEqual(search_chunks_full_text(self.connection, "missing' OR TRUE --", "replica lag"), [])
        self.assertEqual([m["chunk_id"] for m in search_chunks_full_text(self.connection, "old-index", "replica nonexistent")],
                         ["z", "a", "b", "partial"])

    def test_empty_stopword_only_punctuation_and_unmatched_queries_return_no_rows(self):
        for question in ("", "the and or", "!!!", "nonexistent"):
            with self.subTest(question=question):
                self.assertEqual(search_chunks_full_text(self.connection, "old-index", question), [])

    def test_quoted_query_is_text_and_does_not_bypass_index_membership(self):
        matches = search_chunks_full_text(self.connection, "new-index", "lag' OR TRUE --")
        self.assertEqual([match["chunk_id"] for match in matches], ["new"])

    def test_search_leaves_the_callers_transaction_uncommitted(self):
        self.assertTrue(search_chunks_full_text(self.connection, "old-index", "replica lag"))
        self.connection.rollback()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT to_regclass('pg_temp.chunks')")
            self.assertIsNone(cursor.fetchone()[0])


if __name__ == "__main__":
    unittest.main()
