"""Opt-in PostgreSQL tests using temporary tables and rollback only."""

import os
import unittest

from rag_workflow_lab.config import load_database_settings
from rag_workflow_lab.store import save_chunks, save_snapshots


@unittest.skipUnless(os.environ.get("RAG_LAB_TEST_DB") == "1", "Set RAG_LAB_TEST_DB=1 for local DB tests.")
class CorpusStoreTests(unittest.TestCase):
    def setUp(self):
        import psycopg

        self.driver = psycopg
        self.connection = psycopg.connect(
            **load_database_settings().connect_kwargs(), options="-c statement_timeout=5000",
        )
        self.addCleanup(self.connection.close)
        with self.connection.cursor() as cursor:
            cursor.execute("CREATE TEMP TABLE source_snapshots (LIKE public.source_snapshots INCLUDING ALL)")
            cursor.execute("CREATE TEMP TABLE chunks (LIKE public.chunks INCLUDING ALL)")
            cursor.execute("ALTER TABLE chunks ADD FOREIGN KEY (snapshot_id) REFERENCES source_snapshots (snapshot_id)")
        self.snapshot = {
            "snapshot_id": "fixture-snapshot", "source": {"source_id": "fixture", "title": "Fixture", "url": "https://example.org"},
            "sha256": "fixture-hash", "downloaded_at": "2026-11-12T00:00:00Z",
        }
        self.chunk = {
            "chunk_id": "fixture-chunk", "snapshot_id": "fixture-snapshot",
            "text": "SELECT 'quoted';\n  -- Unicode: π", "embedding_text": "search_document: Fixture",
            "token_count": 12, "source_id": "fixture", "heading_path": ["SQL"],
            "anchors": ["example"], "blocks": [{"kind": "code", "text": "SELECT 'quoted';"}],
            "tokenizer": {"revision": "pinned"}, "previous_chunk_id": None,
        }

    def counts(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT (SELECT count(*) FROM source_snapshots), (SELECT count(*) FROM chunks)")
            return cursor.fetchone()

    def test_round_trip_and_repeated_import_preserve_exact_contents(self):
        for _ in range(2):
            save_snapshots(self.connection, [self.snapshot])
            save_chunks(self.connection, [self.chunk])
        self.assertEqual(self.counts(), (1, 1))
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT chunk_id, snapshot_id, text, embedding_text, token_count, metadata FROM chunks")
            chunk_id, snapshot_id, text, embedding_text, tokens, metadata = cursor.fetchone()
        self.assertEqual({**metadata, "chunk_id": chunk_id, "snapshot_id": snapshot_id,
                          "text": text, "embedding_text": embedding_text, "token_count": tokens}, self.chunk)

    def test_existing_ids_cannot_silently_change(self):
        save_snapshots(self.connection, [self.snapshot])
        save_chunks(self.connection, [self.chunk])
        changes = [
            (save_snapshots, {**self.snapshot, "sha256": "changed"}),
            (save_chunks, {**self.chunk, "text": "changed"}),
            (save_chunks, {**self.chunk, "heading_path": ["changed"]}),
        ]
        for save, record in changes:
            with self.subTest(record=record), self.assertRaisesRegex(ValueError, "differs"):
                with self.connection.transaction():
                    save(self.connection, [record])
        self.assertEqual(self.counts(), (1, 1))
        save_snapshots(self.connection, [self.snapshot])
        save_chunks(self.connection, [self.chunk])

    def test_chunk_failure_rolls_back_snapshot_in_the_same_transaction(self):
        with self.assertRaises(self.driver.IntegrityError):
            with self.connection.transaction():
                save_snapshots(self.connection, [self.snapshot])
                save_chunks(self.connection, [{**self.chunk, "token_count": 0}])
        self.assertEqual(self.counts(), (0, 0))


if __name__ == "__main__":
    unittest.main()
