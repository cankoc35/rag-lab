"""LLM-only request isolation and trace lifecycle without API or DB access."""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from rag_workflow_lab.config import GeneratorSettings
from rag_workflow_lab.workflows.llm_only import answer_question


class LlmOnlyTests(unittest.TestCase):
    def setUp(self):
        self.writer, self.client = MagicMock(), MagicMock()
        self.writer.autocommit = True
        self.generator = GeneratorSettings("gpt-6-luna")
        self.start = self.enterContext(patch("rag_workflow_lab.workflows.llm_only.start_trace", return_value="trace"))
        self.span = self.enterContext(patch("rag_workflow_lab.workflows.llm_only.start_span", return_value="span"))
        self.finish = self.enterContext(patch("rag_workflow_lab.workflows.llm_only.finish_trace"))
        self.finish_span = self.enterContext(patch("rag_workflow_lab.workflows.llm_only.finish_span"))
        self.response = SimpleNamespace(id="response", model="gpt-6-luna", status="completed",
                                        output_text="An answer from prior knowledge.", usage=None, incomplete_details=None)
        self.client.responses.create.return_value = self.response

    def run_question(self):
        return answer_question(self.writer, self.client, self.generator, "Raw question?",
                               run_id="batch", question_id="P01", configuration={"dataset_version": "1.0"})

    def test_only_raw_question_and_generic_instructions_enter_one_request(self):
        with patch("rag_workflow_lab.tracing.retrieve") as retrieve, \
                patch("rag_workflow_lab.embeddings.NomicEmbedder.from_local") as load_model:
            result = self.run_question()
        retrieve.assert_not_called()
        load_model.assert_not_called()
        self.client.responses.create.assert_called_once()
        request = self.client.responses.create.call_args.kwargs
        self.assertEqual(request["input"], "Raw question?")
        self.assertIn("own knowledge", request["instructions"])
        self.assertIn("PostgreSQL 18", request["instructions"])
        self.assertFalse({"tools", "conversation", "previous_response_id"} & request.keys())
        self.assertEqual(request["reasoning"], {"effort": "none"})
        self.assertEqual(request["max_output_tokens"], 1000)
        self.assertFalse(request["store"])
        self.assertEqual(result["sources"], [])

    def test_one_trace_contains_one_llm_span_and_exact_input(self):
        result = self.run_question()
        self.assertEqual(self.start.call_args.args[1:], ("Raw question?", "llm_only"))
        self.assertEqual(self.start.call_args.kwargs["question_id"], "P01")
        self.assertEqual(self.start.call_args.kwargs["configuration"]["retrieval"], {"enabled": False})
        self.span.assert_called_once()
        self.assertEqual(self.span.call_args.args[1:4], ("trace", "llm", "answer"))
        self.assertEqual(self.span.call_args.args[4]["sources"], [])
        self.assertEqual(self.span.call_args.args[4]["prompt"], "Raw question?")
        self.finish.assert_called_once_with(self.writer, "trace", answer=result["answer"], error=None)
        self.assertIsNone(self.finish_span.call_args.kwargs["usage"])
        self.assertTrue(result["ok"])

    def test_partial_or_empty_output_is_an_error_and_reported_usage_is_kept(self):
        usage = {"input_tokens": 10, "output_tokens": 3, "total_tokens": 13}
        self.response.usage = SimpleNamespace(model_dump=lambda **kwargs: usage)
        for status, text in (("incomplete", "Partial"), ("completed", "")):
            with self.subTest(status=status):
                self.response.status, self.response.output_text = status, text
                self.assertFalse(self.run_question()["ok"])
                self.assertEqual(self.finish_span.call_args.kwargs["usage"], usage)
                self.assertEqual(self.finish_span.call_args.kwargs["outputs"]["answer"], text)
                self.assertIsNotNone(self.finish.call_args.kwargs["error"])

    def test_provider_exception_is_sanitized_and_not_retried(self):
        self.client.responses.create.side_effect = RuntimeError("secret-provider-message")
        with self.assertRaises(RuntimeError):
            self.run_question()
        self.client.responses.create.assert_called_once()
        self.assertNotIn("secret-provider-message", json.dumps(self.finish_span.call_args.kwargs))
        self.assertIsNotNone(self.finish.call_args.kwargs["error"])

    def test_non_autocommit_writer_is_rejected_before_any_write_or_request(self):
        self.writer.autocommit = False
        with self.assertRaisesRegex(ValueError, "autocommit"):
            self.run_question()
        self.start.assert_not_called()
        self.client.responses.create.assert_not_called()

    def test_span_logging_must_succeed_before_paid_request(self):
        self.span.side_effect = RuntimeError("Writer unavailable")
        with self.assertRaises(RuntimeError):
            self.run_question()
        self.client.responses.create.assert_not_called()
        self.finish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
