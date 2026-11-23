"""Index identity checks without models, database drivers or network access."""

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from rag_workflow_lab.config import EmbeddingSettings
from rag_workflow_lab.embeddings import MODEL_ID, MODEL_REVISION
from scripts.index_corpus import build_index, main


class IndexIdentityTests(unittest.TestCase):
    def setUp(self):
        self.embedding = EmbeddingSettings(MODEL_ID, MODEL_REVISION, Path("unused"))
        self.chunks = [("b", "search_document: Second", 5), ("a", "search_document: First", 5)]
        self.runtime = {"libraries": {"torch": "fixture"}, "model_manifest_sha256": "a" * 64}

    def test_row_and_dictionary_order_do_not_change_index_identity(self):
        index = build_index(self.chunks, self.embedding, self.runtime)
        repeated = build_index(list(reversed(self.chunks)), self.embedding,
                               dict(reversed(list(self.runtime.items()))))
        self.assertEqual(index, repeated)
        self.assertTrue(index["index_id"].startswith("nomic-"))
        self.assertEqual(index["settings"]["max_tokens"], self.embedding.max_tokens)

    def test_chunk_membership_and_exact_input_changes_create_a_different_index(self):
        original = build_index(self.chunks, self.embedding, self.runtime)
        for chunks in (self.chunks[:1], [("other", text, tokens) for _, text, tokens in self.chunks],
                       [(cid, text + " ", tokens) for cid, text, tokens in self.chunks]):
            with self.subTest(chunks=chunks):
                changed = build_index(chunks, self.embedding, self.runtime)
                self.assertNotEqual(changed["chunk_set_sha256"], original["chunk_set_sha256"])
                self.assertNotEqual(changed["index_id"], original["index_id"])

    def test_model_revision_budget_and_runtime_changes_create_a_different_index(self):
        original = build_index(self.chunks, self.embedding, self.runtime)
        for embedding, runtime in (
            (replace(self.embedding, revision="b" * 40), self.runtime),
            (replace(self.embedding, max_tokens=512), self.runtime),
            (self.embedding, {**self.runtime, "libraries": {"torch": "changed"}}),
            (self.embedding, {**self.runtime, "model_manifest_sha256": "b" * 64}),
        ):
            with self.subTest(embedding=embedding, runtime=runtime):
                changed = build_index(self.chunks, embedding, runtime)
                self.assertEqual(changed["chunk_set_sha256"], original["chunk_set_sha256"])
                self.assertNotEqual(changed["index_id"], original["index_id"])

    def test_cli_reports_progress_before_model_loading_and_keeps_stdout_json(self):
        output, progress = StringIO(), StringIO()
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.cursor.return_value.__enter__.return_value.fetchall.return_value = self.chunks[:1]
        result = SimpleNamespace(token_count=5)
        embedder = SimpleNamespace(settings=self.embedding, embed_document=Mock(return_value=result))
        driver = SimpleNamespace(Error=RuntimeError, connect=Mock(return_value=connection))

        def load_model(settings):
            self.assertIn("Loading local model", progress.getvalue())
            return embedder

        with (
            patch.dict(sys.modules, {"psycopg": driver}),
            patch.dict("os.environ", {}),
            patch("sys.argv", ["scripts/index_corpus.py"]),
            patch("scripts.index_corpus.load_settings", return_value=SimpleNamespace(embedding=self.embedding)),
            patch("scripts.index_corpus.load_database_settings", return_value=SimpleNamespace(connect_kwargs=lambda: {})),
            patch("scripts.index_corpus.NomicEmbedder.from_local", side_effect=load_model),
            patch("scripts.index_corpus.file_sha256", return_value="a" * 64),
            patch("scripts.index_corpus.version", return_value="fixture"),
            patch("scripts.index_corpus.save_embedding_index"),
            patch("scripts.index_corpus.save_embeddings"),
            redirect_stdout(output), redirect_stderr(progress),
        ):
            main()
        self.assertEqual(json.loads(output.getvalue())["status"], "indexed")
        for message in ("Starting corpus indexing", "Model loaded", "Connecting to PostgreSQL",
                        "Embedding chunk 1/1", "Saving index and embeddings", "Index committed"):
            self.assertIn(message, progress.getvalue())

    def test_cli_rejects_mixed_source_and_snapshot_selection_before_loading(self):
        with (patch("sys.argv", ["index_corpus.py", "--source-id", "fixture", "--snapshot-id", "snapshot"]),
              patch("scripts.index_corpus.NomicEmbedder.from_local") as load,
              redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error):
            main()
        self.assertEqual(error.exception.code, 2)
        load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
