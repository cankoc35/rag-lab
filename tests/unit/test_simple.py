"""Evidence isolation, one-call generation and workflow trace ownership; no API/DB."""

import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from rag_workflow_lab.config import EmbeddingSettings, GeneratorSettings
from rag_workflow_lab.embeddings import MODEL_ID, MODEL_REVISION
from rag_workflow_lab.llm import build_answer_input
from rag_workflow_lab.workflows.simple import answer_question


class SimpleTests(unittest.TestCase):
    def setUp(self):
        self.reader, self.writer, self.client = MagicMock(), MagicMock(), MagicMock()
        self.writer.autocommit = True
        self.embedder = SimpleNamespace(settings=EmbeddingSettings(MODEL_ID, MODEL_REVISION, Path("unused")))
        self.generator = GeneratorSettings("gpt-6-luna")
        self.matches = [{"chunk_id": "chunk", "snapshot_id": "snapshot", "source_id": "PG-STATS",
                         "title": "Fixture", "url": "https://example.org", "distance": 0.25,
                         "token_count": 20, "text": "Whole SQL: SELECT 'π';\nDo not split this block.",
                         "expected_answer": "GOLD MUST NOT ENTER THE PROMPT"}]
        self.start = self.enterContext(patch("rag_workflow_lab.workflows.simple.start_trace", return_value="trace"))
        self.span = self.enterContext(patch("rag_workflow_lab.workflows.simple.start_span", return_value="llm-span"))
        self.finish = self.enterContext(patch("rag_workflow_lab.workflows.simple.finish_trace"))
        self.finish_span = self.enterContext(patch("rag_workflow_lab.workflows.simple.finish_span"))
        self.retrieve = self.enterContext(patch("rag_workflow_lab.workflows.simple.retrieve_with_trace",
                                               return_value=(self.matches, "trace")))
        self.response = SimpleNamespace(id="response", model="gpt-6-luna", status="completed",
                                        output_text="Documented answer [S1].", usage=None, incomplete_details=None)
        self.client.responses.create.return_value = self.response

    def run_question(self):
        return answer_question(self.reader, self.writer, self.embedder, self.client, self.generator,
                               "index", "Raw question?", run_id="batch", question_id="P04")

    def test_context_preserves_whole_text_and_excludes_unselected_gold_fields(self):
        prompt, sources = build_answer_input("Raw question?", self.matches * 2)
        payload = json.loads(prompt)
        self.assertEqual(payload["question"], "Raw question?")
        self.assertEqual([s["label"] for s in sources], ["S1", "S2"])
        self.assertEqual(payload["sources"][0]["text"], self.matches[0]["text"])
        self.assertEqual(sources[0]["chunk_id"], "chunk")
        self.assertNotIn("text", sources[0])
        self.assertNotIn("GOLD", prompt)

    def test_one_call_and_both_operations_share_the_workflow_trace(self):
        result = self.run_question()
        self.retrieve.assert_called_once_with(self.reader, self.writer, self.embedder,
                                              "index", "Raw question?", trace_id="trace")
        self.client.responses.create.assert_called_once()
        request = self.client.responses.create.call_args.kwargs
        self.assertEqual(request["input"], build_answer_input("Raw question?", self.matches)[0])
        self.assertNotIn("GOLD", request["instructions"] + request["input"])
        self.assertNotIn("tools", request)
        self.assertFalse(request["store"])
        self.assertEqual(self.span.call_args.args[1:4], ("trace", "llm", "answer"))
        self.assertEqual(self.span.call_args.args[4]["prompt"], request["input"])
        self.finish.assert_called_once_with(self.writer, "trace", answer=result["answer"], error=None)
        self.assertTrue(result["ok"])
        self.assertIsNone(self.finish_span.call_args.kwargs["usage"])

    def test_empty_context_is_explicit_and_instructions_allow_abstention(self):
        self.matches.clear()
        self.run_question()
        request = self.client.responses.create.call_args.kwargs
        self.assertEqual(json.loads(request["input"])["sources"], [])
        self.assertIn("insufficient", request["instructions"])

    def test_partial_or_empty_generation_is_an_error_but_keeps_text_and_usage(self):
        usage = {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}
        self.response.usage = MagicMock()
        self.response.usage.model_dump.return_value = usage
        for status, answer in (("incomplete", "Partial"), ("completed", "  ")):
            with self.subTest(status=status):
                self.response.status, self.response.output_text = status, answer
                result = self.run_question()
                self.assertFalse(result["ok"])
                self.assertEqual(result["answer"], answer)
                self.assertEqual(self.finish_span.call_args.kwargs["usage"], usage)
                self.assertIsNotNone(self.finish.call_args.kwargs["error"])

    def test_provider_failure_is_sanitized_and_does_not_retry(self):
        self.client.responses.create.side_effect = RuntimeError("secret-provider-message")
        with self.assertRaises(RuntimeError):
            self.run_question()
        self.client.responses.create.assert_called_once()
        self.assertNotIn("secret-provider-message", json.dumps(self.finish_span.call_args.kwargs))
        self.assertIsNotNone(self.finish.call_args.kwargs["error"])

    def test_retrieval_failure_closes_root_without_calling_llm(self):
        self.retrieve.side_effect = RuntimeError("secret-database-message")
        with self.assertRaises(RuntimeError):
            self.run_question()
        self.client.responses.create.assert_not_called()
        self.span.assert_not_called()
        self.assertNotIn("secret-database-message", json.dumps(self.finish.call_args.kwargs))

    def test_logging_failure_after_generation_does_not_report_success(self):
        self.finish_span.side_effect = RuntimeError("Writer unavailable")
        with self.assertRaises(RuntimeError):
            self.run_question()
        self.finish.assert_not_called()
        self.client.responses.create.assert_called_once()

    def test_llm_span_must_be_persisted_before_paid_call(self):
        self.span.side_effect = RuntimeError("Writer unavailable")
        with self.assertRaises(RuntimeError):
            self.run_question()
        self.client.responses.create.assert_not_called()
        self.finish.assert_not_called()

    def test_separate_autocommit_writer_is_required_before_any_write(self):
        self.writer.autocommit = False
        with self.assertRaisesRegex(ValueError, "separate autocommit"):
            self.run_question()
        self.start.assert_not_called()
        self.client.responses.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
