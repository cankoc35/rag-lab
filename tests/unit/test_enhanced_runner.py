"""Enhanced CLI selection, resource reuse and safe partial reports; no DB/API/models."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

from rag_workflow_lab.config import GeneratorSettings
from scripts import run_enhanced_rag as runner


class EnhancedRunnerTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.dataset = self.root / "questions.json"
        self.dataset.write_text(json.dumps({"source_state": {"source_state_id": "fixture"}, "questions": [
            {"question_id": qid, "question": f"Raw {qid}?", "expected_answer": "GOLD_MUST_NOT_LEAK"}
            for qid in ("P07", "P19", "P05")]}))
        (self.root / "configs").mkdir()
        (self.root / "configs/reranker.toml").write_text(
            '[reranker]\nmodel_id="fixture/reranker"\nrevision="pinned"\nmodels_dir="../models"\n'
            'device="mps"\ndtype="float16"\nmax_tokens=2048\ninstruction="Score the passage."\n')
        self.reader, self.writer, self.client = MagicMock(), MagicMock(), MagicMock()
        for resource in (self.reader, self.writer, self.client):
            resource.__enter__.return_value = resource
        self.connect = Mock(side_effect=[self.reader, self.writer])
        self.openai = Mock(return_value=self.client)
        self.enterContext(patch.dict("sys.modules", {
            "psycopg": SimpleNamespace(connect=self.connect),
            "openai": SimpleNamespace(OpenAI=self.openai),
        }))
        self.enterContext(patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-secret"}))
        self.enterContext(patch.object(runner, "ROOT", self.root))
        self.enterContext(patch.object(runner, "DATASET", self.dataset))
        self.validate = self.enterContext(patch.object(runner, "validate", return_value={"dataset_version": "fixture"}))
        self.scope = self.enterContext(patch.object(runner, "validate_index_scope"))
        self.enterContext(patch.object(runner, "get_embedding_index", return_value={"index_id": "index"}))
        self.enterContext(patch.object(runner, "load_database_settings", return_value=SimpleNamespace(connect_kwargs=lambda: {})))
        self.enterContext(patch.object(runner, "load_settings", return_value=SimpleNamespace(
            embedding=SimpleNamespace(model_dir=self.root), generator=GeneratorSettings("gpt-6-luna"))))
        self.embedding_loader = self.enterContext(patch.object(runner.NomicEmbedder, "from_local"))
        self.model, self.tokenizer = Mock(), Mock()
        self.reranker_loader = self.enterContext(patch.object(runner, "load_reranker", return_value=(self.model, self.tokenizer)))
        self.score = self.enterContext(patch.object(runner, "score", return_value=.99))
        self.enterContext(patch.object(runner, "file_sha256", return_value="fixture-hash"))
        self.enterContext(patch.object(runner, "version", return_value="fixture-version"))
        self.enterContext(patch.object(runner.subprocess, "check_output", side_effect=["fixture-head", " M fixture"]))
        self.answer = self.enterContext(patch.object(runner, "answer_question", side_effect=self.success))
        self.stdout = self.enterContext(redirect_stdout(StringIO()))
        self.stderr = self.enterContext(redirect_stderr(StringIO()))

    def success(self, *args, **kwargs):
        args[6](args[5], "Policy\n\nWhole source block.")
        return {"ok": True, "outcome": "answered", "trace_id": "trace-" + kwargs["question_id"],
                "answer": "Answer [S1].", "sources": [{"label": "S1", "chunk_id": "chunk"}],
                "generation": {"response": {"usage": {"input_tokens": 30, "output_tokens": 10}}}}

    def run_cli(self, *selection):
        return runner.main(["--index-id", "index", "--call-api", *(selection or ("--all",))])

    def read_report(self):
        summary = json.loads(self.stdout.getvalue())
        return summary, json.loads(Path(summary["report"]).read_text())

    def test_all_reuses_models_connections_client_and_links_raw_question_records(self):
        self.assertEqual(self.run_cli(), 0)
        summary, report = self.read_report()
        self.assertEqual((summary["processed"], summary["answered"], summary["abstained"], summary["error"]), (3, 3, 0, 0))
        self.assertEqual(report["report_type"], "enhanced_answers")
        self.assertEqual(report["mode"], "threshold_sufficiency")
        self.assertEqual(report["requested_questions"], 3)
        self.assertFalse(report["batch_stopped_on_error"])
        self.assertEqual([q["question_id"] for q in report["questions"]], ["P07", "P19", "P05"])
        self.assertEqual({call.kwargs["run_id"] for call in self.answer.call_args_list}, {report["run_id"]})
        for call in self.answer.call_args_list:
            self.assertEqual(call.kwargs["writer"], self.writer)
            self.assertEqual(call.kwargs["reranker_settings"]["revision"], "pinned")
            self.assertEqual(call.kwargs["configuration"]["dataset_sha256"], "fixture-hash")
            self.assertEqual(call.args[:3], (self.reader, self.embedding_loader.return_value, self.client))
        self.embedding_loader.assert_called_once()
        self.reranker_loader.assert_called_once()
        self.assertEqual(self.reranker_loader.call_args.args[1], (self.root / "models/fixture--reranker/pinned").resolve())
        self.assertEqual(self.connect.call_count, 2)
        self.assertTrue(self.reader.read_only)
        self.assertTrue(self.connect.call_args_list[1].kwargs["autocommit"])
        self.openai.assert_called_once_with(base_url="https://api.openai.com/v1", timeout=30, max_retries=0)
        self.assertEqual(self.score.call_count, 3)
        self.assertIn("scoring candidate 1", self.stderr.getvalue())
        self.assertIn("reranker_files_sha256", report)
        self.assertIn("load_seconds", report)
        self.assertNotIn("GOLD_MUST_NOT_LEAK", json.dumps(report))
        self.assertNotIn("fixture-secret", self.stdout.getvalue() + self.stderr.getvalue())

    def test_single_selection_and_independent_mode_are_forwarded(self):
        self.assertEqual(self.run_cli("--question-id", "P19", "--mode", "sufficiency"), 0)
        self.answer.assert_called_once()
        self.assertEqual(self.answer.call_args.args[5], "Raw P19?")
        self.assertEqual(self.answer.call_args.kwargs["mode"], "sufficiency")
        self.scope.assert_called_once_with(self.reader, "index", json.loads(self.dataset.read_text()))

    def test_small_batch_reuses_models_and_preserves_explicit_question_order(self):
        self.assertEqual(self.run_cli("--question-id", "P05", "--question-id", "P07"), 0)
        self.assertEqual([call.args[5] for call in self.answer.call_args_list], ["Raw P05?", "Raw P07?"])
        self.embedding_loader.assert_called_once()
        self.reranker_loader.assert_called_once()

    def test_repeated_or_unknown_ids_in_batch_fail_before_db_or_models(self):
        for qids in (("P07", "P07"), ("P07", "P999")):
            with self.subTest(qids=qids), self.assertRaises(SystemExit):
                self.run_cli("--question-id", qids[0], "--question-id", qids[1])
        self.connect.assert_not_called()
        self.embedding_loader.assert_not_called()

    def test_abstention_is_counted_separately_and_does_not_stop_batch(self):
        self.answer.side_effect = lambda *a, **kw: {"ok": True, "outcome": "abstained", "trace_id": "trace",
                                                   "answer": "Insufficient evidence.", "generation": None}
        self.assertEqual(self.run_cli(), 0)
        summary, report = self.read_report()
        self.assertEqual((summary["answered"], summary["abstained"]), (0, 3))
        self.assertFalse(report["batch_stopped_on_error"])
        self.answer.assert_called()
        self.assertEqual(self.answer.call_count, 3)

    def test_exception_preserves_previous_records_stops_batch_and_hides_provider_message(self):
        self.answer.side_effect = [{"ok": True, "outcome": "answered", "trace_id": "trace-P07", "answer": "Answer [S1]."},
                                   RuntimeError("fixture-secret must not leak")]
        self.assertEqual(self.run_cli(), 2)
        summary, report = self.read_report()
        self.assertEqual((summary["processed"], summary["answered"], summary["error"]), (2, 1, 1))
        self.assertEqual(self.answer.call_count, 2)
        self.assertTrue(report["batch_stopped_on_error"])
        self.assertEqual(report["requested_questions"], 3)
        self.assertIsNone(report["questions"][-1]["trace_id"])
        self.assertNotIn("fixture-secret", json.dumps(report) + self.stderr.getvalue())

    def test_returned_operational_error_is_saved_and_stops_batch(self):
        self.answer.side_effect = None
        self.answer.return_value = {"ok": False, "outcome": "error", "trace_id": "trace",
                                    "answer": "Partial", "generation": {"response": {"status": "incomplete"}}}
        self.assertEqual(self.run_cli(), 2)
        _, report = self.read_report()
        self.answer.assert_called_once()
        self.assertEqual(report["questions"][0]["answer"], "Partial")
        self.assertTrue(report["batch_stopped_on_error"])

    def test_wrong_scope_stops_before_model_loading_writer_or_client(self):
        self.scope.side_effect = ValueError("fixture-secret")
        with self.assertRaises(SystemExit) as caught:
            self.run_cli()
        self.assertEqual(caught.exception.code, 2)
        self.embedding_loader.assert_not_called()
        self.reranker_loader.assert_not_called()
        self.assertEqual(self.connect.call_count, 1)
        self.openai.assert_not_called()
        self.assertNotIn("fixture-secret", self.stderr.getvalue())

    def test_unknown_question_fails_before_db_or_model_access(self):
        with self.assertRaises(SystemExit):
            self.run_cli("--question-id", "P999")
        self.connect.assert_not_called()
        self.reranker_loader.assert_not_called()
        self.openai.assert_not_called()

    def test_paid_calls_require_flag_and_key_before_setup(self):
        with self.assertRaises(SystemExit):
            runner.main(["--index-id", "index", "--all"])
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), self.assertRaises(SystemExit):
            self.run_cli()
        self.validate.assert_not_called()
        self.connect.assert_not_called()

    def test_selection_and_mode_must_be_valid_before_setup(self):
        for options in ([], ["--all", "--question-id", "P07"], ["--all", "--mode", "invalid"]):
            with self.subTest(options=options), self.assertRaises(SystemExit):
                runner.main(["--index-id", "index", "--call-api", *options])
        self.validate.assert_not_called()

    def test_model_load_failure_stops_before_trace_writer_or_paid_client(self):
        self.reranker_loader.side_effect = RuntimeError("fixture-secret")
        with self.assertRaises(SystemExit):
            self.run_cli()
        self.assertEqual(self.connect.call_count, 1)
        self.openai.assert_not_called()
        self.answer.assert_not_called()
        self.assertNotIn("fixture-secret", self.stderr.getvalue())


class RerankerLoadingTests(unittest.TestCase):
    def test_loader_requires_native_local_safetensors_and_evaluation_mode(self):
        torch, factory, tokenizer = MagicMock(), Mock(), Mock()
        model = factory.from_pretrained.return_value.to.return_value.eval.return_value
        with patch.dict("sys.modules", {"torch": torch, "transformers": SimpleNamespace(
                AutoModelForCausalLM=factory, AutoTokenizer=tokenizer)}):
            result = runner.load_reranker({"device": "mps", "dtype": "float16"}, Path("pinned"))
        self.assertEqual(result, (model, tokenizer.from_pretrained.return_value))
        tokenizer.from_pretrained.assert_called_once_with(Path("pinned"), local_files_only=True, trust_remote_code=False)
        factory.from_pretrained.assert_called_once_with(Path("pinned"), local_files_only=True, trust_remote_code=False,
                                                        use_safetensors=True, dtype=torch.float16)
        factory.from_pretrained.return_value.to.assert_called_once_with("mps")
        torch.mps.synchronize.assert_called_once()

    def test_unavailable_mps_fails_without_loading_or_falling_back(self):
        torch, factory = MagicMock(), Mock()
        torch.backends.mps.is_available.return_value = False
        with patch.dict("sys.modules", {"torch": torch, "transformers": SimpleNamespace(
                AutoModelForCausalLM=factory, AutoTokenizer=factory)}), self.assertRaises(ValueError):
            runner.load_reranker({"device": "mps", "dtype": "float16"}, Path("pinned"))
        factory.from_pretrained.assert_not_called()


if __name__ == "__main__":
    unittest.main()
