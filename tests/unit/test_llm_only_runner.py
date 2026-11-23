"""LLM-only CLI isolation and report mapping without network/model/DB access."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from rag_workflow_lab.config import GeneratorSettings
from scripts.run_llm_only import main


class LlmOnlyRunnerTests(unittest.TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        self.dataset = root / "questions.json"
        self.dataset.write_text(json.dumps({"dataset_id": "dev", "dataset_version": "1.0",
            "source_state": {"source_state_id": "fixture"}, "questions": [
                {"question_id": f"P{i:02}", "question": f"Raw question {i}?", "expected_answer": "SECRET GOLD"}
                for i in range(1, 7)
            ]}))
        for name in (
            "scripts/run_llm_only.py", "scripts/run_llm_only.py.lock", "configs/pilot.toml",
            "src/rag_workflow_lab/config.py", "src/rag_workflow_lab/llm.py",
            "src/rag_workflow_lab/evaluation/dataset.py", "src/rag_workflow_lab/tracing.py",
            "src/rag_workflow_lab/workflows/llm_only.py", "src/rag_workflow_lab/prompts/llm_only_v1.md",
        ):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture code")
        self.writer, self.client = MagicMock(), MagicMock()
        self.writer.__enter__.return_value = self.writer
        self.client.__enter__.return_value = self.client
        self.connect = Mock(return_value=self.writer)
        self.openai = Mock(return_value=self.client)
        self.enterContext(patch.dict(sys.modules, {
            "psycopg": SimpleNamespace(connect=self.connect, Error=LookupError),
            "openai": SimpleNamespace(OpenAI=self.openai, OpenAIError=ConnectionError),
        }))
        self.enterContext(patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-key"}))
        self.enterContext(patch("scripts.run_llm_only.ROOT", root))
        self.enterContext(patch("scripts.run_llm_only.DATASET", self.dataset))
        self.enterContext(patch("scripts.run_llm_only.load_settings", return_value=SimpleNamespace(generator=GeneratorSettings("gpt-6-luna"))))
        self.enterContext(patch("scripts.run_llm_only.load_database_settings", return_value=SimpleNamespace(connect_kwargs=lambda: {})))
        self.enterContext(patch("scripts.run_llm_only.version", return_value="fixture-version"))
        self.enterContext(patch("scripts.run_llm_only.subprocess.check_output", side_effect=["fixture-head", " M fixture"]))
        self.answer = self.enterContext(patch("scripts.run_llm_only.answer_question", side_effect=lambda *args, **kwargs: {
            "trace_id": "trace-" + kwargs["question_id"], "status": "completed", "ok": True,
            "answer": "Answer from prior knowledge.", "sources": [], "usage": None,
        }))
        self.stdout = self.enterContext(redirect_stdout(StringIO()))
        self.stderr = self.enterContext(redirect_stderr(StringIO()))

    def test_all_mode_needs_no_corpus_and_uses_only_one_trace_writer(self):
        self.assertEqual(main(["--all", "--call-api"]), 0)
        summary = json.loads(self.stdout.getvalue())
        report = json.loads(Path(summary["report"]).read_text())
        self.assertEqual((report["workflow"], report["retrieval_enabled"]), ("llm_only", False))
        self.assertEqual((summary["questions"], summary["completed_answers"]), (6, 6))
        self.assertEqual([q["question_id"] for q in report["questions"]], [f"P{i:02}" for i in range(1, 7)])
        self.assertTrue(all(q["sources"] == [] for q in report["questions"]))
        self.assertNotIn("SECRET GOLD", json.dumps(report))
        self.assertNotIn("fixture-key", json.dumps(report))
        self.assertNotIn("index", report)
        self.connect.assert_called_once_with(autocommit=True, options="-c statement_timeout=5000")
        self.openai.assert_called_once_with(base_url="https://api.openai.com/v1", timeout=30, max_retries=0)
        for i, call in enumerate(self.answer.call_args_list, 1):
            self.assertEqual(call.args[-1], f"Raw question {i}?")
            self.assertEqual(call.kwargs["run_id"], report["run_id"])
            self.assertEqual(call.kwargs["question_id"], f"P{i:02}")

    def test_single_mode_preserves_the_selected_raw_question(self):
        self.assertEqual(main(["--question-id", "P04", "--call-api"]), 0)
        self.answer.assert_called_once()
        self.assertEqual(self.answer.call_args.args[-1], "Raw question 4?")

    def test_explicit_atlas_dataset_needs_no_corpus_and_keeps_gold_outside_calls(self):
        path = self.dataset.with_name("atlas.json")
        dataset = json.loads(self.dataset.read_text())
        dataset.update(dataset_id="atlas-fixture", source_state={
            "source_state_id": "atlas-fixture-state", "sources_manifest": {"path": "MISSING-CORPUS.json"}})
        dataset["questions"] = [{"question_id": qid, "question": f"Raw {qid}?",
                                  "expected_answer": "SECRET GOLD", "evidence": [{"text": "SECRET EVIDENCE"}]}
                                 for qid in ("P07", "P08", "P09", "P19")]
        path.write_text(json.dumps(dataset))
        self.assertEqual(main(["--dataset", str(path), "--all", "--call-api"]), 0)
        self.assertEqual([call.args[-1] for call in self.answer.call_args_list], [q["question"] for q in dataset["questions"]])
        report = json.loads(Path(json.loads(self.stdout.getvalue())["report"]).read_text())
        self.assertEqual(report["dataset_path"], str(path.resolve()))
        self.assertEqual(report["dataset"]["dataset_id"], "atlas-fixture")
        self.assertFalse(report["retrieval_enabled"])
        self.assertNotIn("SECRET GOLD", json.dumps(report))
        self.assertNotIn("SECRET EVIDENCE", json.dumps(report))
        self.assertEqual(self.connect.call_count, 1)

    def test_unknown_id_fails_before_connecting_to_db_or_api(self):
        with self.assertRaises(SystemExit) as caught:
            main(["--question-id", "P99", "--call-api"])
        self.assertEqual(caught.exception.code, 2)
        self.connect.assert_not_called()
        self.openai.assert_not_called()

    def test_selection_is_required_and_mutually_exclusive(self):
        for selection in ([], ["--all", "--question-id", "P01"]):
            with self.subTest(selection=selection), self.assertRaises(SystemExit):
                main([*selection, "--call-api"])
        self.openai.assert_not_called()

    def test_paid_calls_require_flag_and_key(self):
        with self.assertRaises(SystemExit):
            main(["--all"])
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), self.assertRaises(SystemExit):
            main(["--all", "--call-api"])
        self.connect.assert_not_called()
        self.openai.assert_not_called()

    def test_incomplete_reply_is_saved_and_returns_exit_code_two(self):
        self.answer.side_effect = None
        self.answer.return_value = {"trace_id": "trace", "status": "incomplete", "ok": False,
                                    "answer": "Partial", "sources": [], "usage": {"output_tokens": 2}}
        self.assertEqual(main(["--question-id", "P01", "--call-api"]), 2)
        summary = json.loads(self.stdout.getvalue())
        report = json.loads(Path(summary["report"]).read_text())
        self.assertEqual(summary["completed_answers"], 0)
        self.assertEqual(report["questions"][0]["answer"], "Partial")
        self.assertEqual(report["questions"][0]["usage"], {"output_tokens": 2})

    def test_provider_failure_is_sanitized_and_stops_without_retry(self):
        self.answer.side_effect = ConnectionError("secret-provider-message")
        with self.assertRaises(SystemExit) as caught:
            main(["--all", "--call-api"])
        self.assertEqual(caught.exception.code, 2)
        self.answer.assert_called_once()
        self.assertNotIn("secret-provider-message", self.stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
