"""Trace lifecycle, safe payload and retrieval-link checks without PostgreSQL."""

import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from uuid import UUID

from rag_workflow_lab.config import EmbeddingSettings
from rag_workflow_lab.embeddings import MODEL_ID, MODEL_REVISION
from rag_workflow_lab.tracing import finish_span, finish_trace, retrieve_with_trace, start_span, start_trace


class TraceWriterTests(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.cursor = self.connection.cursor.return_value.__enter__.return_value
        self.cursor.rowcount = 1

    def test_attempts_have_distinct_ids_and_bind_question_text_as_a_parameter(self):
        question = "Can NULL mean 'zero'? -- π"
        first = start_trace(self.connection, question, "dense_retrieval", run_id="batch", question_id="P04")
        second = start_trace(self.connection, question, "dense_retrieval")
        self.assertNotEqual(first, second)
        self.assertEqual(UUID(first).version, 4)
        sql, params = self.cursor.execute.call_args_list[0].args
        self.assertNotIn(question, sql)
        self.assertEqual(params[:5], (first, "batch", "P04", "dense_retrieval", question))
        self.assertEqual(json.loads(params[5]), {})
        self.connection.commit.assert_not_called()

    def test_span_payloads_keep_parent_usage_cost_and_unknown_values_separate(self):
        span_id = start_span(self.connection, "trace", "llm", "answer", {"messages": ["question"]}, parent_span_id="parent")
        self.assertEqual(self.cursor.execute.call_args.args[1][1:5], ("trace", "parent", "llm", "answer"))
        usage = {"input_tokens": 20, "output_tokens": 5, "total_tokens": 25}
        cost = {"amount": 0.01, "currency": "USD", "source": "estimate"}
        finish_span(self.connection, span_id, outputs={"answer": "Answer [S1]"}, usage=usage, cost=cost)
        params = self.cursor.execute.call_args.args[1]
        self.assertEqual(params[0], "ok")
        self.assertEqual(json.loads(params[2]), usage)
        self.assertEqual(json.loads(params[3]), cost)
        finish_span(self.connection, "other-span")
        self.assertEqual(self.cursor.execute.call_args.args[1][1:5], (None, None, None, None))

    def test_error_finalization_and_already_finished_records_are_explicit(self):
        error = {"type": "EmbeddingError", "message": "Embedding failed."}
        finish_trace(self.connection, "trace", error=error)
        self.assertEqual(self.cursor.execute.call_args.args[1], ("error", None, json.dumps(error), "trace"))
        self.cursor.rowcount = 0
        for finish in (finish_trace, finish_span):
            with self.subTest(function=finish.__name__), self.assertRaisesRegex(ValueError, "already finished"):
                finish(self.connection, "missing")

    def test_nonfinite_payloads_fail_before_sql(self):
        with self.assertRaises(ValueError):
            start_trace(self.connection, "question", "simple", configuration={"value": float("nan")})
        self.cursor.execute.assert_not_called()


class TracedRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.reader, self.writer = MagicMock(), MagicMock()
        self.writer.autocommit = True
        self.embedder = SimpleNamespace(settings=EmbeddingSettings(MODEL_ID, MODEL_REVISION, Path("unused")))
        self.matches = [{"chunk_id": "chunk", "snapshot_id": "snapshot", "source_id": "source",
                         "url": "https://example.org", "title": "Fixture", "token_count": 12,
                         "distance": 0.25, "text": "Body", "metadata": {}}]
        self.start_trace = self.enterContext(patch("rag_workflow_lab.tracing.start_trace", return_value="trace"))
        self.start_span = self.enterContext(patch("rag_workflow_lab.tracing.start_span", return_value="span"))
        self.finish_trace = self.enterContext(patch("rag_workflow_lab.tracing.finish_trace"))
        self.finish_span = self.enterContext(patch("rag_workflow_lab.tracing.finish_span"))
        self.retrieve = self.enterContext(patch("rag_workflow_lab.tracing.retrieve", return_value=self.matches))

    def test_success_preserves_results_and_records_actual_ranks_and_batch_links(self):
        result, trace_id = retrieve_with_trace(self.reader, self.writer, self.embedder, "index", "question",
                                              run_id="batch", question_id="P01", configuration={"dataset_version": "1.0"})
        self.assertIs(result, self.matches)
        self.assertEqual(trace_id, "trace")
        self.retrieve.assert_called_once_with(self.reader, self.embedder, "index", "question", limit=5)
        config = self.start_trace.call_args.kwargs
        self.assertEqual((config["run_id"], config["question_id"]), ("batch", "P01"))
        self.assertEqual(config["configuration"]["embedding"]["model_id"], MODEL_ID)
        chunk = self.finish_span.call_args.kwargs["outputs"]["chunks"][0]
        self.assertEqual((chunk["chunk_id"], chunk["rank"], chunk["distance"]), ("chunk", 1, 0.25))
        self.assertNotIn("text", chunk)
        self.finish_trace.assert_called_once_with(self.writer, "trace")

    def test_retrieval_error_is_recorded_without_copying_sensitive_exception_text(self):
        failure = RuntimeError("password=do-not-log-this")
        self.retrieve.side_effect = failure
        with self.assertRaises(RuntimeError) as caught:
            retrieve_with_trace(self.reader, self.writer, self.embedder, "index", "question")
        self.assertIs(caught.exception, failure)
        error = self.finish_span.call_args.kwargs["error"]
        self.assertEqual(error["type"], "RuntimeError")
        self.assertNotIn("do-not-log-this", json.dumps(error))
        self.finish_trace.assert_called_once_with(self.writer, "trace", error=error)

    def test_writer_must_be_separate_and_autocommit(self):
        self.reader.autocommit = True
        self.writer.autocommit = False
        for writer in (self.reader, self.writer):
            with self.assertRaisesRegex(ValueError, "separate autocommit"):
                retrieve_with_trace(self.reader, writer, self.embedder, "index", "question")
        self.start_trace.assert_not_called()
        self.retrieve.assert_not_called()

    def test_logging_failure_aborts_instead_of_reporting_a_completed_trace(self):
        self.finish_span.side_effect = RuntimeError("Writer unavailable")
        with self.assertRaisesRegex(RuntimeError, "Writer unavailable"):
            retrieve_with_trace(self.reader, self.writer, self.embedder, "index", "question")
        self.finish_trace.assert_not_called()


if __name__ == "__main__":
    unittest.main()
