"""Enhanced answer boundaries and shared generation settings, without DB/API access."""

from copy import deepcopy
from hashlib import sha256
from importlib.resources import files
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from rag_workflow_lab.config import GeneratorSettings
from rag_workflow_lab.workflows.enhanced import PROMPT_VERSION, answer_question
from rag_workflow_lab.workflows.simple import PROMPT_VERSION as SIMPLE_PROMPT_VERSION


class EnhancedAnswerTests(unittest.TestCase):
    def setUp(self):
        self.connection, self.embedder, self.client, self.scorer = (Mock() for _ in range(4))
        self.generator = GeneratorSettings("gpt-6-luna")
        self.matches = [{
            "chunk_id": f"chunk-{rank}", "snapshot_id": "snapshot", "source_id": "policy",
            "title": "Canary policy", "url": "https://example.org/policy",
            "distance": None if rank == 5 else .25, "token_count": 20,
            "text": f"Canary lag must not exceed 5 seconds.\nWhole block {rank}.",
            "metadata": {"heading_path": ["Canary", "Reporting"]},
            "rrf_rank": 6 - rank, "reranker_score": .95 if rank == 1 else .1,
            "expected_answer": "GOLD_MUST_NOT_LEAK",
        } for rank in range(1, 6)]
        self.retrieve = self.enterContext(patch("rag_workflow_lab.workflows.enhanced.retrieve_reranked",
                                               return_value=self.matches))
        self.assessment = {
            "status": "sufficient", "reason": "The policy states the limit.",
            "evidence": [{"source_label": "S1", "quote": "Canary lag must not exceed 5 seconds."}],
            "missing_information": [],
        }
        self.checker = SimpleNamespace(id="check", model="gpt-6-luna", status="completed",
                                       output_text=json.dumps(self.assessment), usage=None, incomplete_details=None)
        self.answer = SimpleNamespace(id="answer", model="gpt-6-luna", status="completed",
                                      output_text="The limit is 5 seconds [S1].", usage=Mock(), incomplete_details=None)
        self.answer.usage.model_dump.return_value = {"input_tokens": 30, "output_tokens": 10, "total_tokens": 40}
        self.client.responses.create.side_effect = [self.checker, self.answer]

    def run_question(self, mode="threshold_sufficiency"):
        return answer_question(self.connection, self.embedder, self.client, self.generator,
                               "index", "What is Canary's lag limit?", self.scorer, mode=mode)

    def test_sufficient_context_uses_shared_answer_prompt_and_preserves_all_five(self):
        original = deepcopy(self.matches)
        result = self.run_question()
        self.assertEqual(result["outcome"], "answered")
        self.assertTrue(result["ok"])
        self.assertEqual(result["answer"], self.answer.output_text)
        self.retrieve.assert_called_once_with(self.connection, self.embedder, "index",
                                              "What is Canary's lag limit?", self.scorer)
        self.assertEqual(self.client.responses.create.call_count, 2)
        checker, answer = [call.kwargs for call in self.client.responses.create.call_args_list]
        self.assertEqual(checker["text"]["format"]["name"], "sufficiency_v1")
        self.assertNotIn("text", answer)
        self.assertEqual(PROMPT_VERSION, SIMPLE_PROMPT_VERSION)
        instructions = files("rag_workflow_lab").joinpath(f"prompts/{SIMPLE_PROMPT_VERSION}.md").read_text()
        self.assertEqual(answer["instructions"], instructions)
        payload = json.loads(answer["input"])
        self.assertEqual(payload["question"], "What is Canary's lag limit?")
        self.assertEqual([s["text"] for s in payload["sources"]], [m["text"] for m in original])
        self.assertEqual([s["label"] for s in result["sources"]], [f"S{n}" for n in range(1, 6)])
        self.assertEqual([s["chunk_id"] for s in result["sources"]], [m["chunk_id"] for m in original])
        self.assertIsNone(result["sources"][-1]["distance"])
        self.assertEqual(result["retrieved_chunks"], original)
        self.assertEqual(self.matches, original)
        for request in (checker, answer):
            self.assertNotIn("GOLD", request["input"])
            self.assertNotIn("reranker_score", request["input"])
            self.assertNotIn("tools", request)
            self.assertEqual(request["model"], self.generator.model_id)
            self.assertEqual(request["reasoning"], {"effort": "none"})
            self.assertEqual(request["max_output_tokens"], 1000)
            self.assertEqual(request["service_tier"], "default")
            self.assertFalse(request["store"])
        generation = result["generation"]
        self.assertEqual(generation["instructions_sha256"], sha256(instructions.encode()).hexdigest())
        self.assertEqual(generation["prompt"], answer["input"])
        self.assertEqual(generation["response"]["response_id"], "answer")
        self.assertEqual(generation["response"]["usage"]["total_tokens"], 40)
        self.assertEqual(result["evidence_check"]["response"]["response_id"], "check")
        self.client.close.assert_not_called()
        self.connection.close.assert_not_called()

    def test_low_gate_and_empty_context_abstain_without_api_resources(self):
        self.matches[0]["reranker_score"] = .94
        for matches in (self.matches, []):
            with self.subTest(empty=not matches):
                self.retrieve.return_value = matches
                result = answer_question(self.connection, self.embedder, None, None, "index",
                                         "Question?", self.scorer, mode="threshold_sufficiency")
                self.assertEqual(result["outcome"], "abstained")
                self.assertTrue(result["ok"])
                self.assertIn("insufficient", result["answer"])
                self.assertEqual(result["context"], [])
                self.assertEqual(result["retrieved_chunks"], matches)
                self.assertIsNone(result["generation"])
        self.client.responses.create.assert_not_called()

    def test_partial_or_insufficient_checker_never_reaches_answer_generation(self):
        for status in ("partial", "insufficient"):
            with self.subTest(status=status):
                self.assessment.update(status=status, missing_information=["Another requested fact is missing."])
                self.checker.output_text = json.dumps(self.assessment)
                self.client.responses.create.side_effect = [self.checker]
                self.client.responses.create.reset_mock()
                result = self.run_question()
                self.assertEqual(result["outcome"], "abstained")
                self.assertTrue(result["ok"])
                self.assertIsNone(result["generation"])
                self.client.responses.create.assert_called_once()

    def test_invalid_checker_is_an_error_without_answer_or_abstention(self):
        invalid_quote = {**self.assessment, "evidence": [{"source_label": "S1", "quote": "Limit is 8 seconds."}]}
        for output in ("not JSON", json.dumps(invalid_quote)):
            with self.subTest(output=output):
                self.checker.output_text = output
                self.client.responses.create.side_effect = [self.checker]
                self.client.responses.create.reset_mock()
                result = self.run_question()
                self.assertEqual(result["outcome"], "error")
                self.assertFalse(result["ok"])
                self.assertIsNone(result["answer"])
                self.assertIsNone(result["generation"])
                self.assertEqual(result["evidence_check"]["response"]["answer"], output)
                self.client.responses.create.assert_called_once()

    def test_independent_controls_keep_their_call_counts(self):
        for mode in ("baseline", "threshold", "sufficiency"):
            with self.subTest(mode=mode):
                self.client.responses.create.side_effect = ([self.checker] if mode == "sufficiency" else []) + [self.answer]
                self.client.responses.create.reset_mock()
                result = self.run_question(mode)
                self.assertTrue(result["ok"])
                self.assertEqual(self.client.responses.create.call_count, 2 if mode == "sufficiency" else 1)

    def test_incomplete_or_empty_answer_is_an_error_and_preserves_raw_response(self):
        for status, text in (("incomplete", "Partial answer"), ("completed", "  ")):
            with self.subTest(status=status):
                self.answer.status, self.answer.output_text = status, text
                self.answer.incomplete_details = SimpleNamespace(reason="max_output_tokens") if status == "incomplete" else None
                self.client.responses.create.side_effect = [self.checker, self.answer]
                result = self.run_question()
                self.assertFalse(result["ok"])
                self.assertEqual(result["outcome"], "error")
                self.assertEqual(result["answer"], text)
                self.assertEqual(result["generation"]["response"]["usage"]["total_tokens"], 40)
                self.assertEqual(result["generation"]["response"]["status"], status)

    def test_provider_failure_in_either_call_propagates_without_retry(self):
        for responses in ([RuntimeError("checker failed")], [self.checker, RuntimeError("answer failed")]):
            with self.subTest(call=len(responses)):
                self.client.responses.create.side_effect = responses
                self.client.responses.create.reset_mock()
                with self.assertRaises(RuntimeError):
                    self.run_question()
                self.assertEqual(self.client.responses.create.call_count, len(responses))


if __name__ == "__main__":
    unittest.main()
