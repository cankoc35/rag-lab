"""Pinned-input checks, paid opt-in and auditable failures for evidence comparisons."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from rag_workflow_lab.config import GeneratorSettings
from scripts import check_evidence


class EvidenceRunnerTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(patch.object(check_evidence, "ROOT", self.root))
        self.stdout, self.stderr = StringIO(), StringIO()
        self.enterContext(redirect_stdout(self.stdout))
        self.enterContext(redirect_stderr(self.stderr))
        self.enterContext(patch.object(check_evidence.subprocess, "check_output", return_value="fixture-head"))
        self.enterContext(patch.object(check_evidence, "load_settings", return_value=SimpleNamespace(
            generator=GeneratorSettings("gpt-6-luna"))))
        for path in ("scripts/check_evidence.py", "scripts/check_evidence.py.lock", "configs/pilot.toml",
                     "src/rag_workflow_lab/evidence.py", "src/rag_workflow_lab/llm.py",
                     "src/rag_workflow_lab/prompts/sufficiency_v1.md"):
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("fixture")
        chunks = [{"chunk_id": f"c{i}", "text": f"Whole passage {i}.", "heading_path": ["Fixture"]}
                  for i in range(20)]
        (self.root / "chunks.json").write_text(json.dumps({"chunks": chunks}))
        self.dataset = {"source_state": {"sources": [{
            "source_id": "source", "snapshot_id": "snapshot", "files": {"chunks": {"path": "chunks.json"}},
        }]}, "questions": [
            {"question_id": "P1", "question": "Raw question?", "expected_answer": "GOLD_MUST_NOT_LEAK"},
            {"question_id": "P2", "question": "Another question?", "expected_answer": "GOLD_MUST_NOT_LEAK"},
        ]}
        self.dataset_path = self.root / "dataset.json"
        self.dataset_path.write_text(json.dumps(self.dataset))
        dataset_hash = sha256(self.dataset_path.read_bytes()).hexdigest()
        self.enterContext(patch.object(check_evidence, "validate", return_value={"dataset_sha256": dataset_hash}))
        ranking = [{"chunk_id": f"c{i}", "source_id": "source", "snapshot_id": "snapshot",
                    "reranker_score": .96 if i == 0 else .1, "rrf_rank": i + 1} for i in range(20)]
        self.report = {"report_type": "reranker_probe", "candidate_limit": 20,
                       "dataset": {"dataset_sha256": dataset_hash}, "index": {"index_id": "fixture"},
                       "settings": {"model_id": "fixture-reranker"},
                       "questions": [{**q, "ranking": deepcopy(ranking)} for q in self.dataset["questions"]]}
        self.report_path = self.root / "report.json"
        self.save_report()

    def save_report(self):
        self.report_path.write_text(json.dumps(self.report))

    def args(self, mode):
        return ["--mode", mode, "--dataset", str(self.dataset_path), "--report", str(self.report_path), "--all"]

    def output(self):
        path = Path(json.loads(self.stdout.getvalue())["report"])
        return json.loads(path.read_text())

    def test_offline_threshold_keeps_exact_five_chunks_and_no_gold_runtime_fields(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            self.assertEqual(check_evidence.main(self.args("threshold")), 0)
        report = self.output()
        self.assertFalse(report["database_access"])
        self.assertFalse(report["reranker_inference"])
        self.assertFalse(report["answer_generation"])
        self.assertIsNone(report["checker_settings"])
        self.assertEqual(report["selected_questions"], 2)
        self.assertNotIn("GOLD_MUST_NOT_LEAK", json.dumps(report["questions"]))
        self.assertEqual(len(report["questions"][0]["context"]), 5)
        self.assertEqual(report["questions"][0]["context"][4]["reranker_score"], .1)
        self.assertTrue(report["questions"][0]["evidence_check"]["allowed"])

    def test_sufficiency_requires_opt_in_and_key_before_reading_inputs(self):
        with patch.object(check_evidence, "load_contexts") as load:
            with self.assertRaises(SystemExit) as error:
                check_evidence.main(self.args("sufficiency"))
            self.assertEqual(error.exception.code, 2)
            with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), self.assertRaises(SystemExit):
                check_evidence.main(self.args("sufficiency") + ["--call-api"])
        load.assert_not_called()

    def test_combined_all_gates_rejected_runs_without_key_or_sdk_client(self):
        for row in self.report["questions"]:
            row["ranking"][0]["reranker_score"] = .94
        self.save_report()
        factory = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), \
                patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=factory)}):
            self.assertEqual(check_evidence.main(self.args("threshold_sufficiency")), 0)
        report = self.output()
        self.assertIsNone(report["checker_settings"])
        self.assertEqual(len(report["questions"]), 2)
        for row in report["questions"]:
            self.assertFalse(row["evidence_check"]["checker_called"])
            self.assertEqual(row["evidence_check"]["decision"], "score_reject")
            self.assertEqual(len(row["context"]), 5)
        factory.assert_not_called()

    def test_combined_call_api_flag_still_skips_client_when_all_gates_reject(self):
        for row in self.report["questions"]:
            row["ranking"][0]["reranker_score"] = .94
        self.save_report()
        factory = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), \
                patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=factory)}):
            self.assertEqual(check_evidence.main(self.args("threshold_sufficiency") + ["--call-api"]), 0)
        factory.assert_not_called()

    def test_combined_passing_gate_requires_opt_in_and_key_before_sdk_client(self):
        factory = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), \
                patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=factory)}):
            for extra in ([], ["--call-api"]):
                with self.subTest(extra=extra), self.assertRaises(SystemExit) as error:
                    check_evidence.main(self.args("threshold_sufficiency") + extra)
                self.assertEqual(error.exception.code, 2)
        factory.assert_not_called()

    def test_combined_mixed_batch_only_calls_checker_for_gate_pass(self):
        self.report["questions"][0]["ranking"][0]["reranker_score"] = .94
        self.save_report()
        factory = MagicMock()
        client = factory.return_value.__enter__.return_value
        client.responses.create.return_value = SimpleNamespace(
            id="response", model="gpt-6-luna", status="completed", usage=None, incomplete_details=None,
            output_text=json.dumps({"status": "sufficient", "reason": "The passage supplies the fact.",
                                    "evidence": [{"source_label": "S1", "quote": "Whole passage 0."}],
                                    "missing_information": []}))
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-key"}), \
                patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=factory)}):
            self.assertEqual(check_evidence.main(self.args("threshold_sufficiency") + ["--call-api"]), 0)
        report = self.output()
        self.assertFalse(report["questions"][0]["evidence_check"]["checker_called"])
        self.assertTrue(report["questions"][1]["evidence_check"]["checker_called"])
        self.assertTrue(report["questions"][1]["evidence_check"]["allowed"])
        self.assertEqual(report["checker_settings"]["model_id"], "gpt-6-luna")
        client.responses.create.assert_called_once()
        self.assertEqual(json.loads(client.responses.create.call_args.kwargs["input"])["question"],
                         "Another question?")
        factory.assert_called_once_with(base_url="https://api.openai.com/v1", timeout=30, max_retries=0)

    def test_combined_provider_error_blocks_and_stops_without_retry(self):
        factory = MagicMock()
        client = factory.return_value.__enter__.return_value
        client.responses.create.side_effect = RuntimeError("fixture-secret")
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-key"}), \
                patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=factory)}):
            self.assertEqual(check_evidence.main(self.args("threshold_sufficiency") + ["--call-api"]), 2)
        report = self.output()
        self.assertTrue(report["batch_stopped_on_error"])
        self.assertEqual(len(report["questions"]), 1)
        self.assertFalse(report["questions"][0]["evidence_check"]["allowed"])
        self.assertEqual(report["questions"][0]["evidence_check"]["decision"], "error")
        self.assertNotIn("fixture-secret", json.dumps(report))
        client.responses.create.assert_called_once()

    def test_bad_report_pins_questions_sources_and_rankings_are_rejected(self):
        original = deepcopy(self.report)
        variants = []
        for field, value in (("report_type", "dense"), ("candidate_limit", 5),
                             ("dataset", {"dataset_sha256": "wrong"})):
            changed = deepcopy(original)
            changed[field] = value
            variants.append(changed)
        changed = deepcopy(original)
        changed["questions"][0]["question"] = "Altered question"
        variants.append(changed)
        changed = deepcopy(original)
        changed["questions"][0]["ranking"][0]["snapshot_id"] = "wrong-state"
        variants.append(changed)
        changed = deepcopy(original)
        changed["questions"][0]["ranking"].reverse()
        variants.append(changed)
        changed = deepcopy(original)
        changed["questions"].append(changed["questions"][0])
        variants.append(changed)
        for report in variants:
            with self.subTest(report=report):
                self.report = report
                self.save_report()
                with self.assertRaises(ValueError):
                    check_evidence.load_contexts(self.dataset_path, self.report_path, None)

    def test_paid_error_is_saved_without_provider_secrets_and_stops_the_batch(self):
        factory = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-key"}), \
                patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=factory)}), \
                patch.object(check_evidence, "assess_evidence", side_effect=RuntimeError("fixture-key")):
            self.assertEqual(check_evidence.main(self.args("sufficiency") + ["--call-api"]), 2)
        report = self.output()
        self.assertTrue(report["batch_stopped_on_error"])
        self.assertEqual(report["selected_questions"], 2)
        self.assertEqual(len(report["questions"]), 1)
        self.assertEqual(report["questions"][0]["evidence_check"]["decision"], "error")
        self.assertNotIn("fixture-key", json.dumps(report) + self.stderr.getvalue())
        factory.assert_called_once_with(base_url="https://api.openai.com/v1", timeout=30, max_retries=0)

    def test_valid_sufficiency_rejection_completes_and_records_checker_settings(self):
        factory = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "fixture-key"}), \
                patch.dict("sys.modules", {"openai": SimpleNamespace(OpenAI=factory)}), \
                patch.object(check_evidence, "assess_evidence", return_value={
                    "mode": "sufficiency", "allowed": False, "decision": "partial"}) as assess:
            self.assertEqual(check_evidence.main(self.args("sufficiency") + ["--call-api"]), 0)
        report = self.output()
        self.assertFalse(report["batch_stopped_on_error"])
        self.assertEqual(len(report["questions"]), 2)
        self.assertEqual(report["checker_settings"]["model_id"], "gpt-6-luna")
        self.assertEqual(assess.call_count, 2)
        self.assertFalse(report["answer_generation"])

    def test_model_assessment_error_is_not_counted_as_normal_abstention(self):
        with patch.object(check_evidence, "assess_evidence", return_value={
                "allowed": False, "decision": "error", "error": "Invalid quoted evidence."}):
            self.assertEqual(check_evidence.main(self.args("baseline")), 2)
        self.assertTrue(self.output()["batch_stopped_on_error"])


if __name__ == "__main__":
    unittest.main()
