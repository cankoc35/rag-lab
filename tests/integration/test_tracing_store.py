"""Opt-in tracing tests after migration 0002; writes use session-local tables."""

import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from rag_workflow_lab.config import EmbeddingSettings, GeneratorSettings, load_database_settings
from rag_workflow_lab.embeddings import MODEL_ID, MODEL_REVISION
from rag_workflow_lab.tracing import finish_span, finish_trace, retrieve_with_trace, start_span, start_trace
from rag_workflow_lab.workflows.simple import answer_question
from rag_workflow_lab.workflows.llm_only import answer_question as answer_without_retrieval


@unittest.skipUnless(os.environ.get("RAG_LAB_TEST_DB") == "1", "Set RAG_LAB_TEST_DB=1 for local DB tests.")
class TracingStoreTests(unittest.TestCase):
    def setUp(self):
        import psycopg

        self.driver = psycopg
        self.writer = psycopg.connect(**load_database_settings().connect_kwargs(),
                                      autocommit=True, options="-c statement_timeout=5000")
        self.addCleanup(self.writer.close)
        with self.writer.cursor() as cursor:
            cursor.execute("SELECT to_regclass('public.traces'), to_regclass('public.spans')")
            if None in cursor.fetchone():
                self.skipTest("Requires the owner-approved application of migration 0002.")
            cursor.execute("CREATE TEMP TABLE traces (LIKE public.traces INCLUDING ALL)")
            cursor.execute("CREATE TEMP TABLE spans (LIKE public.spans INCLUDING ALL)")
            cursor.execute("ALTER TABLE spans ADD FOREIGN KEY (trace_id) REFERENCES traces (trace_id)")
            cursor.execute("ALTER TABLE spans ADD FOREIGN KEY (trace_id, parent_span_id) REFERENCES spans (trace_id, span_id)")

    def test_round_trip_preserves_prompt_usage_cost_and_source_payloads(self):
        trace_id = start_trace(self.writer, "Can NULL mean 'zero'?", "simple", run_id="batch", question_id="P04")
        span_id = start_span(self.writer, trace_id, "llm", "answer", {"messages": ["Question π"]})
        outputs = {"answer": "Insufficient evidence.", "context_chunk_ids": ["chunk"]}
        usage = {"input_tokens": 20, "output_tokens": 5, "total_tokens": 25}
        finish_span(self.writer, span_id, outputs=outputs, usage=usage)
        finish_trace(self.writer, trace_id, answer=outputs["answer"])
        with self.writer.cursor() as cursor:
            cursor.execute("SELECT status, final_answer, finished_at >= started_at FROM traces WHERE trace_id=%s", (trace_id,))
            self.assertEqual(cursor.fetchone(), ("ok", outputs["answer"], True))
            cursor.execute("SELECT outputs, usage, cost, error FROM spans WHERE span_id=%s", (span_id,))
            self.assertEqual(cursor.fetchone(), (outputs, usage, None, None))

    def test_a_parent_span_cannot_belong_to_another_question(self):
        first = start_trace(self.writer, "First question", "simple")
        second = start_trace(self.writer, "Second question", "simple")
        parent = start_span(self.writer, first, "tool", "inspect", {})
        with self.assertRaises(self.driver.IntegrityError):
            start_span(self.writer, second, "tool", "child", {}, parent_span_id=parent)
        child = start_span(self.writer, first, "tool", "child", {}, parent_span_id=parent)
        self.assertNotEqual(parent, child)

    def test_simple_workflow_persists_both_spans_prompt_and_actual_usage(self):
        embedder = SimpleNamespace(settings=EmbeddingSettings(MODEL_ID, MODEL_REVISION, Path("unused")))
        matches = [{"chunk_id": "chunk", "snapshot_id": "snapshot", "source_id": "PG-STATS",
                    "title": "Fixture", "url": "https://example.org", "distance": 0.25,
                    "token_count": 20, "text": "Whole source text."}]
        for status in ("completed", "incomplete"):
            result = {"response_id": "response", "model": "gpt-6-luna", "status": status,
                      "answer": "Answer [S1]", "usage": {"input_tokens": 10, "output_tokens": 3},
                      "incomplete_reason": None if status == "completed" else "max_output_tokens"}
            with self.subTest(status=status), \
                    patch("rag_workflow_lab.tracing.retrieve", return_value=matches), \
                    patch("rag_workflow_lab.workflows.simple.generate_text", return_value=result):
                observed = answer_question(object(), self.writer, embedder, object(), GeneratorSettings("gpt-6-luna"),
                                           "index", "Raw question?", question_id="P04")
                trace_id = observed["trace_id"]
                with self.writer.cursor() as cursor:
                    cursor.execute("SELECT status, final_answer, question_id FROM traces WHERE trace_id=%s", (trace_id,))
                    self.assertEqual(cursor.fetchone(), ("ok" if observed["ok"] else "error", result["answer"], "P04"))
                    cursor.execute("SELECT kind, status, inputs, usage, cost FROM spans WHERE trace_id=%s ORDER BY started_at",
                                   (trace_id,))
                    retrieval, llm = cursor.fetchall()
                self.assertEqual(retrieval[:2], ("retrieval", "ok"))
                self.assertEqual(llm[:2], ("llm", "ok" if observed["ok"] else "error"))
                self.assertIn("Whole source text.", llm[2]["prompt"])
                self.assertEqual(llm[2]["sources"][0]["chunk_id"], "chunk")
                self.assertEqual(llm[3:], (result["usage"], None))

    def test_completed_observations_cannot_be_overwritten(self):
        trace_id = start_trace(self.writer, "Question", "simple")
        span_id = start_span(self.writer, trace_id, "retrieval", "dense", {})
        finish_span(self.writer, span_id, outputs={"chunks": []})
        finish_trace(self.writer, trace_id, answer="Original answer")
        with self.assertRaises(ValueError):
            finish_span(self.writer, span_id, outputs={"changed": True})
        with self.assertRaises(ValueError):
            finish_trace(self.writer, trace_id, answer="Changed answer")

    def test_llm_only_persists_one_llm_span_with_no_source_context(self):
        for status in ("completed", "incomplete"):
            response = {"response_id": "response", "model": "gpt-6-luna", "status": status,
                        "answer": "Answer from prior knowledge.", "usage": {"input_tokens": 10, "output_tokens": 3},
                        "incomplete_reason": None if status == "completed" else "max_output_tokens"}
            with self.subTest(status=status), patch("rag_workflow_lab.workflows.llm_only.generate_text", return_value=response):
                result = answer_without_retrieval(self.writer, object(), GeneratorSettings("gpt-6-luna"),
                                                 "Raw question?", question_id="P01", run_id="batch")
                with self.writer.cursor() as cursor:
                    cursor.execute("SELECT workflow, status, final_answer FROM traces WHERE trace_id=%s", (result["trace_id"],))
                    self.assertEqual(cursor.fetchone(), ("llm_only", "ok" if result["ok"] else "error", response["answer"]))
                    cursor.execute("SELECT kind, inputs, usage, cost FROM spans WHERE trace_id=%s", (result["trace_id"],))
                    rows = cursor.fetchall()
                self.assertEqual(len(rows), 1)
                kind, inputs, usage, cost = rows[0]
                self.assertEqual((kind, inputs["prompt"], inputs["sources"]), ("llm", "Raw question?", []))
                self.assertEqual(usage, response["usage"])
                self.assertIsNone(cost)

    def test_error_records_survive_retrieval_transaction_rollback(self):
        reader = self.driver.connect(**load_database_settings().connect_kwargs())
        self.addCleanup(reader.close)
        reader.read_only = True
        with self.assertRaises(self.driver.Error):
            reader.execute("SELECT 1 / 0")
        embedder = SimpleNamespace(settings=EmbeddingSettings(MODEL_ID, MODEL_REVISION, Path("unused")))
        with self.assertRaises(self.driver.Error):
            retrieve_with_trace(reader, self.writer, embedder, "unused", "Question")
        reader.rollback()
        with self.writer.cursor() as cursor:
            cursor.execute("SELECT t.status, s.status, t.error = s.error, s.usage FROM traces t JOIN spans s USING (trace_id)")
            self.assertEqual(cursor.fetchone(), ("error", "error", True, None))


if __name__ == "__main__":
    unittest.main()
