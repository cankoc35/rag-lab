"""Check reference ranks and cutoff coverage without models or a database."""

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, call, patch

from scripts.check_retrieval import check_retrieval, main, validate_index_scope


class CheckRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (49,)
        self.embedder = Mock()
        self.matches = [{
            "chunk_id": f"chunk-{i}", "source_id": "fixture", "snapshot_id": "snapshot",
            "url": "https://example.org", "distance": i / 100, "token_count": 10,
        } for i in range(1, 50)]
        self.question = {
            "question_id": "P01", "question": "Which index can be used?", "expected_answer": "Gold must not reach retrieval.",
            "evidence": [{"evidence_id": name, "chunk_id": f"chunk-{rank}"}
                         for name, rank in (("E1", 5), ("E2", 10), ("E3", 20), ("E4", 21), ("E5", 50))],
        }
        self.search = self.enterContext(patch("scripts.check_retrieval.retrieve", return_value=self.matches))
        self.enterContext(redirect_stderr(StringIO()))

    def test_cutoff_boundaries_and_missing_evidence_have_explicit_ranks(self):
        result = check_retrieval(self.connection, self.embedder, "index", {"questions": [self.question]})
        record = result["questions"][0]
        self.assertEqual(result["cutoffs"], [5, 10, 20])
        self.assertEqual(record["evidence_ranks"], {"E1": 5, "E2": 10, "E3": 20, "E4": 21, "E5": None})
        self.assertEqual(record["evidence_hits_at_k"], {
            "5": ["E1"], "10": ["E1", "E2"], "20": ["E1", "E2", "E3"],
        })
        self.assertEqual(len(record["ranking"]), 49)
        self.assertEqual(record["ranking"][0]["snapshot_id"], "snapshot")

    def test_each_original_question_is_retrieved_once_without_gold(self):
        second = {**self.question, "question_id": "P02", "question": "Can lag be NULL?"}
        check_retrieval(self.connection, self.embedder, "index", {"questions": [self.question, second]})
        self.assertEqual(self.search.call_args_list, [
            call(self.connection, self.embedder, "index", self.question["question"], limit=49),
            call(self.connection, self.embedder, "index", second["question"], limit=49),
        ])
        self.connection.commit.assert_not_called()

    def test_an_empty_index_fails_before_retrieving_questions(self):
        self.connection.cursor.return_value.__enter__.return_value.fetchone.return_value = (0,)
        with self.assertRaisesRegex(ValueError, "no stored vectors"):
            check_retrieval(self.connection, self.embedder, "empty", {"questions": [self.question]})
        self.search.assert_not_called()

    def test_unanswerable_question_keeps_its_ranking_without_positive_hit_scoring(self):
        question = {**self.question, "question_id": "P19", "answerability": "unanswerable", "evidence": []}
        progress = StringIO()
        with redirect_stderr(progress):
            result = check_retrieval(self.connection, self.embedder, "index", {"questions": [question]})
        record = result["questions"][0]
        self.assertFalse(record["positive_evidence_applicable"])
        self.assertEqual(record["answerability"], "unanswerable")
        self.assertEqual(record["evidence_ranks"], {})
        self.assertEqual(len(record["ranking"]), 49)
        self.assertIn("N/A (no positive evidence", progress.getvalue())
        self.assertNotIn("0/0", progress.getvalue())

    def test_index_scope_requires_exact_pinned_membership_snapshots_and_inputs(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            text = "search_document: A pinned source"
            (root / "chunks.json").write_text(json.dumps({"chunks": [{"chunk_id": "chunk", "embedding_text": text}]}))
            dataset = {"source_state": {"sources": [{"snapshot_id": "snapshot", "files": {"chunks": {"path": "chunks.json"}}}]}}
            row = ("chunk", "snapshot", text, sha256(text.encode()).hexdigest())
            cursor = self.connection.cursor.return_value.__enter__.return_value
            with patch("scripts.check_retrieval.ROOT", root):
                cursor.fetchall.return_value = [row]
                validate_index_scope(self.connection, "index", dataset)
                for rows in ([], [row, ("extra", *row[1:])], [("chunk", "other-snapshot", *row[2:])],
                             [("chunk", "snapshot", text + "changed", row[3])], [(*row[:3], "0" * 64)]):
                    with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, "complete pinned chunk/input scope"):
                        cursor.fetchall.return_value = rows
                        validate_index_scope(self.connection, "index", dataset)
        self.embedder.assert_not_called()

    def test_cli_passes_an_explicit_dataset_to_reference_validation_before_model_loading(self):
        validate = Mock(side_effect=ValueError("fixture validation stop"))
        with (
            patch.dict(sys.modules, {"psycopg": SimpleNamespace(Error=RuntimeError),
                                    "check_document_questions": SimpleNamespace(validate=validate)}),
            patch("sys.argv", ["check_retrieval.py", "--index-id", "index", "--dataset", "atlas.json"]),
            patch("scripts.check_retrieval.NomicEmbedder.from_local") as load_model,
            self.assertRaises(SystemExit) as stopped,
        ):
            main()
        self.assertEqual(stopped.exception.code, 2)
        validate.assert_called_once_with(Path("atlas.json"))
        load_model.assert_not_called()

    def test_tracing_links_each_question_to_its_trace_and_batch_without_changing_ranks(self):
        writer = Mock()
        with patch("scripts.check_retrieval.retrieve_with_trace", return_value=(self.matches, "trace")) as traced:
            result = check_retrieval(self.connection, self.embedder, "index", {"questions": [self.question]},
                                     trace_connection=writer, run_id="batch", configuration={"dataset_version": "1.0"})
        traced.assert_called_once_with(self.connection, writer, self.embedder, "index", self.question["question"],
                                       limit=49, run_id="batch", question_id="P01", configuration={"dataset_version": "1.0"})
        self.assertEqual(result["questions"][0]["trace_id"], "trace")
        self.assertEqual(result["questions"][0]["evidence_ranks"]["E3"], 20)
        self.search.assert_not_called()

    def test_cli_trace_flag_opens_a_writer_and_preserves_the_batch_link_in_json(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "questions.json"
            dataset.write_text(json.dumps({"source_state": {"source_state_id": "fixture-state"}}))
            reader, writer = MagicMock(), MagicMock()
            reader.__enter__.return_value = reader
            writer.__enter__.return_value = writer
            driver = SimpleNamespace(Error=RuntimeError, connect=Mock(side_effect=[reader, writer]))
            embedding = SimpleNamespace(model_dir=root)
            result = {"questions": [{"question_id": "P01", "trace_id": "trace"}]}
            output = StringIO()
            with (
                patch.dict(sys.modules, {"psycopg": driver, "check_document_questions": SimpleNamespace(validate=Mock(return_value={"dataset_version": "fixture"}))}),
                patch.dict("os.environ", {}),
                patch("sys.argv", ["check_retrieval.py", "--index-id", "index", "--trace"]),
                patch("scripts.check_retrieval.ROOT", root),
                patch("scripts.check_retrieval.DATASET", dataset),
                patch("scripts.check_retrieval.load_settings", return_value=SimpleNamespace(embedding=embedding)),
                patch("scripts.check_retrieval.load_database_settings", return_value=SimpleNamespace(connect_kwargs=lambda: {})),
                patch("scripts.check_retrieval.NomicEmbedder.from_local", return_value=self.embedder),
                patch("scripts.check_retrieval.get_embedding_index", return_value={"index_id": "index"}),
                patch("scripts.check_retrieval.validate_index_scope"),
                patch("scripts.check_retrieval.check_retrieval", return_value=result) as check,
                patch("scripts.check_retrieval.file_sha256", return_value="fixture-hash"),
                patch("scripts.check_retrieval.version", return_value="fixture-version"),
                patch("scripts.check_retrieval.subprocess.check_output", side_effect=["fixture-head", " M fixture"]),
                redirect_stdout(output),
            ):
                main()
            report = json.loads(Path(json.loads(output.getvalue())["report"]).read_text())
            self.assertTrue(reader.read_only)
            self.assertTrue(driver.connect.call_args_list[1].kwargs["autocommit"])
            self.assertIs(check.call_args.kwargs["trace_connection"], writer)
            self.assertEqual(check.call_args.kwargs["run_id"], report["run_id"])
            self.assertTrue(report["retrieval_read_only"] and report["tracing_enabled"])
            self.assertFalse(report["read_only"])
            self.assertEqual(report["questions"][0]["trace_id"], "trace")


if __name__ == "__main__":
    unittest.main()
