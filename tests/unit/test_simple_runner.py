"""Question selection and batch orchestration without API, DB or model access."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from scripts.run_simple_rag import main, run_questions, select_questions


class QuestionTests(unittest.TestCase):
    def setUp(self):
        self.questions = [{"question_id": f"P{i:02}", "question": f"Raw question {i}?",
                           "expected_answer": "Gold must stay outside generation."} for i in range(1, 7)]

    def test_selects_one_question_by_id_and_keeps_only_runtime_fields(self):
        self.assertEqual(select_questions({"questions": self.questions}, "P05"),
                         [{"question_id": "P05", "question": "Raw question 5?"}])

    def test_selects_all_questions_in_dataset_order_without_gold(self):
        selected = select_questions({"questions": self.questions}, None)
        self.assertEqual([q["question_id"] for q in selected], [q["question_id"] for q in self.questions])
        self.assertTrue(all(set(q) == {"question_id", "question"} for q in selected))

    def test_unknown_question_id_is_explicit(self):
        with self.assertRaisesRegex(ValueError, "unknown question ID: P99"):
            select_questions({"questions": self.questions}, "P99")

    def test_batch_preserves_question_mapping_usage_and_shared_run_id(self):
        questions = select_questions({"questions": self.questions}, None)
        results = [{"trace_id": f"trace-{i}", "status": "completed", "ok": True,
                    "answer": f"Answer {i} [S1]", "sources": [{"label": "S1", "chunk_id": f"chunk-{i}"}],
                    "usage": {"input_tokens": i, "output_tokens": 2}} for i in range(1, 7)]
        with patch("scripts.run_simple_rag.answer_question", side_effect=results) as answer, redirect_stderr(StringIO()):
            records = run_questions("reader", "writer", "embedder", "client", "generator", "index",
                                    questions, run_id="batch", configuration={"dataset_version": "1.0"})
        self.assertEqual(answer.call_count, 6)
        for question, result, record, call in zip(questions, results, records, answer.call_args_list):
            self.assertEqual(call.args, ("reader", "writer", "embedder", "client", "generator", "index", question["question"]))
            self.assertEqual(call.kwargs, {"run_id": "batch", "question_id": question["question_id"],
                                           "configuration": {"dataset_version": "1.0"}})
            self.assertEqual(record["question_id"], question["question_id"])
            self.assertTrue(all(record[key] == value for key, value in result.items()))
            self.assertNotIn("expected_answer", record)
            self.assertGreaterEqual(record["elapsed_seconds"], 0)

    def test_exception_stops_batch_without_retrying_or_calling_remaining_questions(self):
        questions = select_questions({"questions": self.questions}, None)
        with patch("scripts.run_simple_rag.answer_question", side_effect=ConnectionError("Failure")) as answer, \
                redirect_stderr(StringIO()), self.assertRaises(ConnectionError):
            run_questions(None, None, None, None, None, "index", questions, run_id="batch", configuration={})
        answer.assert_called_once()


class RunnerCliTests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        self.dataset = root / "questions.json"
        self.dataset.write_text(json.dumps({"source_state": {"source_state_id": "fixture"}, "questions": [
            {"question_id": f"P{i:02}", "question": f"Raw question {i}?", "expected_answer": "SECRET GOLD"}
            for i in range(1, 7)
        ]}))
        self.reader, self.writer, self.client = MagicMock(), MagicMock(), MagicMock()
        for resource in (self.reader, self.writer, self.client):
            resource.__enter__.return_value = resource
        self.connect = Mock(side_effect=[self.reader, self.writer])
        self.openai = Mock(return_value=self.client)
        self.validate = Mock(return_value={"dataset_version": "fixture"})
        self.scope_check = Mock()
        self.enterContext(patch.dict(sys.modules, {
            "psycopg": SimpleNamespace(connect=self.connect, Error=LookupError),
            "openai": SimpleNamespace(OpenAI=self.openai, OpenAIError=ConnectionError),
            "check_document_questions": SimpleNamespace(validate=self.validate),
            "check_retrieval": SimpleNamespace(validate_index_scope=self.scope_check),
        }))
        self.enterContext(patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-key"}))
        self.enterContext(patch("scripts.run_simple_rag.ROOT", root))
        self.enterContext(patch("scripts.run_simple_rag.DATASET", self.dataset))
        self.enterContext(patch("scripts.run_simple_rag.load_settings", return_value=SimpleNamespace(
            embedding=SimpleNamespace(model_dir=root), generator=SimpleNamespace(model_id="gpt-6-luna"))))
        self.enterContext(patch("scripts.run_simple_rag.load_database_settings", return_value=SimpleNamespace(connect_kwargs=lambda: {})))
        self.loader = self.enterContext(patch("scripts.run_simple_rag.NomicEmbedder.from_local"))
        self.enterContext(patch("scripts.run_simple_rag.get_embedding_index", return_value={"index_id": "index"}))
        self.enterContext(patch("scripts.run_simple_rag.file_sha256", return_value="fixture-hash"))
        self.enterContext(patch("scripts.run_simple_rag.version", return_value="fixture-version"))
        self.enterContext(patch("scripts.run_simple_rag.subprocess.check_output", side_effect=["fixture-head", " M fixture"]))
        self.answer = self.enterContext(patch("scripts.run_simple_rag.answer_question", side_effect=lambda *args, **kwargs: {
            "trace_id": "trace-" + kwargs["question_id"], "status": "completed", "ok": True,
            "answer": "Answer [S1]", "sources": [{"label": "S1", "chunk_id": "chunk"}], "usage": None,
        }))
        self.stdout = self.enterContext(redirect_stdout(StringIO()))
        self.stderr = self.enterContext(redirect_stderr(StringIO()))

    def test_all_mode_reuses_resources_and_saves_linked_question_records(self):
        self.assertEqual(main(["--index-id", "index", "--all", "--call-api"]), 0)
        summary = json.loads(self.stdout.getvalue())
        report = json.loads(Path(summary["report"]).read_text())
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual((summary["questions"], summary["completed_answers"]), (6, 6))
        self.assertEqual([q["question_id"] for q in report["questions"]], [f"P{i:02}" for i in range(1, 7)])
        self.assertEqual(len({q["trace_id"] for q in report["questions"]}), 6)
        self.assertEqual({call.kwargs["run_id"] for call in self.answer.call_args_list}, {report["run_id"]})
        self.assertNotIn("SECRET GOLD", json.dumps(report))
        self.assertNotIn("fixture-key", json.dumps(report))
        self.loader.assert_called_once()
        self.openai.assert_called_once_with(base_url="https://api.openai.com/v1", timeout=30, max_retries=0)
        self.assertEqual(self.connect.call_count, 2)
        self.assertTrue(self.reader.read_only)
        self.assertTrue(self.connect.call_args_list[1].kwargs["autocommit"])

    def test_single_mode_calls_only_selected_question(self):
        self.assertEqual(main(["--index-id", "index", "--question-id", "P05", "--call-api"]), 0)
        self.answer.assert_called_once()
        self.assertEqual(self.answer.call_args.args[-1], "Raw question 5?")
        self.assertEqual(self.answer.call_args.kwargs["question_id"], "P05")

    def test_explicit_atlas_dataset_selects_its_questions_without_gold(self):
        path = self.dataset.with_name("atlas.json")
        dataset = {"source_state": {"source_state_id": "atlas-fixture"}, "questions": [
            {"question_id": qid, "question": f"Raw {qid}?", "expected_answer": "SECRET GOLD",
             "answerability": "unanswerable" if qid == "P19" else "answerable"}
            for qid in ("P07", "P08", "P09", "P19")]}
        path.write_text(json.dumps(dataset))
        self.assertEqual(main(["--dataset", str(path), "--index-id", "index", "--all", "--call-api"]), 0)
        self.validate.assert_called_once_with(path)
        self.scope_check.assert_called_once_with(self.reader, "index", dataset)
        self.assertEqual([call.args[-1] for call in self.answer.call_args_list], [q["question"] for q in dataset["questions"]])
        report = json.loads(Path(json.loads(self.stdout.getvalue())["report"]).read_text())
        self.assertEqual(report["dataset_path"], str(path.resolve()))
        self.assertEqual(report["source_state_id"], "atlas-fixture")
        self.assertNotIn("SECRET GOLD", json.dumps(report))

    def test_wrong_index_scope_fails_before_model_loading_trace_writer_or_paid_client(self):
        self.scope_check.side_effect = ValueError("Wrong scope")
        with self.assertRaises(SystemExit) as caught:
            main(["--index-id", "index", "--all", "--call-api"])
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(self.connect.call_count, 1)
        self.loader.assert_not_called()
        self.openai.assert_not_called()
        self.answer.assert_not_called()

    def test_unknown_id_fails_before_model_db_or_api_client_creation(self):
        with self.assertRaises(SystemExit) as caught:
            main(["--index-id", "index", "--question-id", "P99", "--call-api"])
        self.assertEqual(caught.exception.code, 2)
        self.loader.assert_not_called()
        self.connect.assert_not_called()
        self.openai.assert_not_called()

    def test_selection_must_be_explicit_and_mutually_exclusive(self):
        for selection in ([], ["--all", "--question-id", "P01"]):
            with self.subTest(selection=selection), self.assertRaises(SystemExit):
                main(["--index-id", "index", "--call-api", *selection])
        self.validate.assert_not_called()

    def test_paid_calls_require_flag_and_key(self):
        with self.assertRaises(SystemExit):
            main(["--index-id", "index", "--all"])
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), self.assertRaises(SystemExit):
            main(["--index-id", "index", "--all", "--call-api"])
        self.validate.assert_not_called()
        self.openai.assert_not_called()

    def test_incomplete_answer_is_saved_and_returns_nonzero_status(self):
        self.answer.side_effect = None
        self.answer.return_value = {"trace_id": "trace", "status": "incomplete", "ok": False,
                                    "answer": "Partial", "sources": [], "usage": {"output_tokens": 2}}
        self.assertEqual(main(["--index-id", "index", "--question-id", "P01", "--call-api"]), 2)
        summary = json.loads(self.stdout.getvalue())
        report = json.loads(Path(summary["report"]).read_text())
        self.assertEqual(summary["completed_answers"], 0)
        self.assertEqual(report["questions"][0]["answer"], "Partial")
        self.assertEqual(report["questions"][0]["usage"], {"output_tokens": 2})


if __name__ == "__main__":
    unittest.main()
