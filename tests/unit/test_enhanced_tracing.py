"""Enhanced trace lifecycle, stage boundaries and logging failures; no DB/API access."""

import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from rag_workflow_lab.config import EmbeddingSettings, GeneratorSettings
from rag_workflow_lab.workflows.enhanced import answer_question


class EnhancedTracingTests(unittest.TestCase):
    def setUp(self):
        self.reader, self.writer, self.client = Mock(), Mock(), Mock()
        self.writer.autocommit = True
        self.embedder = SimpleNamespace(settings=EmbeddingSettings("embedding", "revision", Path("unused")))
        self.generator = GeneratorSettings("gpt-6-luna")
        self.reranker = dict(model_id="reranker", revision="pinned", device="mps", dtype="float16",
                             max_tokens=2048, instruction="Score the passage.", ignored="DO_NOT_LOG")
        self.matches = [{
            "chunk_id": f"chunk-{n}", "snapshot_id": "snapshot", "source_id": "policy",
            "title": "Policy", "url": "https://example.org", "token_count": 20,
            "text": f"Chunk {n}. Canary lag must not exceed 5 seconds.\nKeep the whole block.",
            "metadata": {"heading_path": ["Canary", "Reporting"], "gold": "DO_NOT_LOG"},
            "distance": .25 if n < 20 else None, "text_score": .1, "dense_rank": n,
            "full_text_rank": n, "rrf_score": 2 / (60 + n), "expected_answer": "DO_NOT_LOG",
        } for n in range(1, 21)]
        self.retrieve = self.enterContext(patch("rag_workflow_lab.tracing.retrieve_hybrid", return_value=self.matches))
        self.scorer = Mock(return_value=.99)
        self.start = self.enterContext(patch("rag_workflow_lab.workflows.enhanced.start_trace", return_value="trace"))
        self.finish = self.enterContext(patch("rag_workflow_lab.workflows.enhanced.finish_trace"))
        self.span = Mock(side_effect=lambda *a, **kw: a[3])
        self.finish_span = Mock()
        for module in ("tracing", "workflows.enhanced"):
            self.enterContext(patch(f"rag_workflow_lab.{module}.start_span", self.span))
            self.enterContext(patch(f"rag_workflow_lab.{module}.finish_span", self.finish_span))
        self.assessment = {"status": "sufficient", "reason": "The policy gives the limit.",
                           "evidence": [{"source_label": "S1", "quote": "Canary lag must not exceed 5 seconds."}],
                           "missing_information": []}
        self.checker = SimpleNamespace(id="check", model="gpt-6-luna", status="completed",
                                       output_text=json.dumps(self.assessment), usage=None, incomplete_details=None)
        self.answer = SimpleNamespace(id="answer", model="gpt-6-luna", status="completed",
                                      output_text="The limit is 5 seconds [S1].", usage=Mock(), incomplete_details=None)
        self.answer.usage.model_dump.return_value = {"input_tokens": 30, "output_tokens": 10}
        self.client.responses.create.side_effect = [self.checker, self.answer]

    def run_question(self, **kwargs):
        return answer_question(self.reader, self.embedder, self.client, self.generator, "index", "Raw question?",
                               self.scorer, mode="threshold_sufficiency", writer=self.writer,
                               reranker_settings=self.reranker, run_id="batch", question_id="P01", **kwargs)

    def starts(self):
        return {call.args[3]: call for call in self.span.call_args_list}

    def finishes(self):
        return {call.args[1]: call.kwargs for call in self.finish_span.call_args_list}

    def test_one_root_preserves_all_candidates_ranking_requests_and_separate_usage(self):
        result = self.run_question(configuration={"dataset_version": "1.8.0", "git_head": "fixture"})
        self.assertEqual(result["trace_id"], "trace")
        self.assertTrue(result["ok"])
        config = self.start.call_args.kwargs
        self.assertEqual(self.start.call_args.args[1:], ("Raw question?", "enhanced"))
        self.assertEqual((config["run_id"], config["question_id"]), ("batch", "P01"))
        self.assertEqual(config["configuration"]["reranker"]["revision"], "pinned")
        self.assertEqual(config["configuration"]["reranker"]["batch_size"], 1)
        self.assertEqual(config["configuration"]["dataset_version"], "1.8.0")
        starts, ends = self.starts(), self.finishes()
        self.assertEqual(list(starts), ["hybrid_retrieval", "rerank", "evidence_check", "sufficiency_check", "answer"])
        self.assertTrue(all(call.args[1] == "trace" for call in starts.values()))
        self.assertEqual(starts["sufficiency_check"].kwargs["parent_span_id"], "evidence_check")
        self.assertEqual(len(ends["hybrid_retrieval"]["outputs"]["chunks"]), 20)
        self.assertEqual(len(ends["rerank"]["outputs"]["ranking"]), 20)
        self.assertEqual(ends["rerank"]["outputs"]["selected_chunk_ids"], [m["chunk_id"] for m in self.matches[:5]])
        self.assertEqual(self.scorer.call_count, 20)
        for name, request in zip(("sufficiency_check", "answer"), self.client.responses.create.call_args_list):
            inputs = starts[name].args[4]
            self.assertEqual(inputs["prompt"], request.kwargs["input"])
            self.assertEqual(inputs["instructions"], request.kwargs["instructions"])
            self.assertEqual([s["text"] for s in json.loads(inputs["prompt"])["sources"]],
                             [m["text"] for m in self.matches[:5]])
        self.assertIsNone(ends["sufficiency_check"]["usage"])
        self.assertEqual(ends["answer"]["usage"], {"input_tokens": 30, "output_tokens": 10})
        self.assertNotIn("usage", ends["evidence_check"])
        self.assertTrue(all(not value.get("error") for value in ends.values()))
        self.assertNotIn("DO_NOT_LOG", str(self.span.call_args_list) + str(self.finish_span.call_args_list) + str(config))
        self.finish.assert_called_once_with(self.writer, "trace", answer=result["answer"], error=None)
        self.writer.commit.assert_not_called()
        self.writer.close.assert_not_called()

    def test_gate_rejection_records_decision_without_llm_span_or_api_resources(self):
        self.scorer.return_value = .94
        self.generator, self.client = None, None
        result = self.run_question()
        self.assertEqual(result["outcome"], "abstained")
        self.assertEqual(list(self.starts()), ["hybrid_retrieval", "rerank", "evidence_check"])
        check = self.finishes()["evidence_check"]["outputs"]
        self.assertEqual(check["decision"], "score_reject")
        self.assertFalse(check["checker_called"])
        self.assertIsNone(self.finish.call_args.kwargs["error"])

    def test_partial_and_insufficient_checks_finish_normally_without_answer_span(self):
        for status in ("partial", "insufficient"):
            with self.subTest(status=status):
                self.assessment.update(status=status, missing_information=["Another requested fact is missing."])
                self.checker.output_text = json.dumps(self.assessment)
                self.client.responses.create.side_effect = [self.checker]
                result = self.run_question()
                self.assertEqual(result["outcome"], "abstained")
                self.assertNotIn("answer", self.starts())
                self.assertIsNone(self.finishes()["evidence_check"]["error"])
                self.assertIsNone(self.finish.call_args.kwargs["error"])

    def test_malformed_checker_output_is_validation_error_not_provider_or_evidence_rejection(self):
        self.checker.output_text = "not JSON"
        result = self.run_question()
        self.assertEqual(result["outcome"], "error")
        self.assertIsNone(result["answer"])
        self.assertIsNone(self.finishes()["sufficiency_check"]["error"])
        self.assertEqual(self.finishes()["evidence_check"]["error"]["type"], "EvidenceCheckError")
        self.assertIsNotNone(self.finish.call_args.kwargs["error"])
        self.assertNotIn("answer", self.starts())

    def test_incomplete_answer_keeps_raw_text_usage_and_marks_span_and_root_error(self):
        self.answer.status = "incomplete"
        self.answer.incomplete_details = SimpleNamespace(reason="max_output_tokens")
        result = self.run_question()
        end = self.finishes()["answer"]
        self.assertFalse(result["ok"])
        self.assertEqual(end["outputs"]["answer"], self.answer.output_text)
        self.assertEqual(end["outputs"]["incomplete_reason"], "max_output_tokens")
        self.assertEqual(end["usage"]["output_tokens"], 10)
        self.assertIsNotNone(end["error"])
        self.assertIsNotNone(self.finish.call_args.kwargs["error"])

    def test_retrieval_or_reranker_failure_records_safe_error_without_any_api_call(self):
        for operation, name in ((self.retrieve, "hybrid_retrieval"), (self.scorer, "rerank")):
            with self.subTest(stage=name):
                operation.side_effect = RuntimeError("DO_NOT_LOG")
                with self.assertRaises(RuntimeError):
                    self.run_question()
                self.assertEqual(self.finishes()[name]["error"]["type"], "RuntimeError")
                operation.side_effect = None
        self.client.responses.create.assert_not_called()
        self.assertNotIn("DO_NOT_LOG", str(self.finish.call_args_list) + str(self.finish_span.call_args_list))

    def test_provider_failure_closes_active_spans_and_root_without_retry(self):
        self.client.responses.create.side_effect = RuntimeError("DO_NOT_LOG")
        with self.assertRaises(RuntimeError):
            self.run_question()
        ends = self.finishes()
        self.assertIsNotNone(ends["sufficiency_check"]["error"])
        self.assertIsNotNone(ends["evidence_check"]["error"])
        self.assertNotIn("answer", self.starts())
        self.client.responses.create.assert_called_once()
        self.assertNotIn("DO_NOT_LOG", str(self.finish.call_args_list) + str(self.finish_span.call_args_list))

    def test_llm_span_write_failure_stops_before_each_paid_call(self):
        for stage, expected_calls in (("sufficiency_check", 0), ("answer", 1)):
            with self.subTest(stage=stage):
                def start(writer, trace_id, kind, name, inputs, **kwargs):
                    if name == stage:
                        raise RuntimeError("Writer unavailable")
                    return name
                self.span.side_effect = start
                self.client.responses.create.side_effect = [self.checker, self.answer]
                self.client.responses.create.reset_mock()
                with self.assertRaises(RuntimeError):
                    self.run_question()
                self.assertEqual(self.client.responses.create.call_count, expected_calls)
                self.assertIsNotNone(self.finish.call_args.kwargs["error"])

    def test_logging_failure_after_model_response_never_reports_success(self):
        for stage, expected_calls in (("sufficiency_check", 1), ("answer", 2)):
            with self.subTest(stage=stage):
                def finish(writer, span_id, **kwargs):
                    if span_id == stage:
                        raise RuntimeError("Writer unavailable")
                self.finish_span.side_effect = finish
                self.client.responses.create.side_effect = [self.checker, self.answer]
                self.client.responses.create.reset_mock()
                with self.assertRaises(RuntimeError):
                    self.run_question()
                self.assertEqual(self.client.responses.create.call_count, expected_calls)
                self.assertIsNotNone(self.finish.call_args.kwargs["error"])

    def test_invalid_writer_and_missing_model_settings_fail_before_starting_work(self):
        self.writer.autocommit = False
        with self.assertRaisesRegex(ValueError, "separate autocommit"):
            self.run_question()
        self.writer.autocommit = True
        self.reranker = None
        with self.assertRaisesRegex(ValueError, "reranker settings"):
            self.run_question()
        self.start.assert_not_called()
        self.retrieve.assert_not_called()
        self.client.responses.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
