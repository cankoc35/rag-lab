"""Evidence policies, source isolation and fail-closed output checks without APIs."""

from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from rag_workflow_lab.config import GeneratorSettings
from rag_workflow_lab.evidence import SCHEMA, assess_evidence
from rag_workflow_lab.workflows.enhanced import prepare_context


def match(score=.99):
    return {"chunk_id": "chunk-a", "snapshot_id": "state-a", "source_id": "policy",
            "text": "Canary reporting lag must not exceed 5 seconds.\nKeep this whole block.",
            "metadata": {"heading_path": ["Canary", "Reporting"]}, "reranker_score": score,
            "expected_answer": "GOLD_MUST_NOT_LEAK"}


def assessment(status="sufficient"):
    return {"status": status, "reason": "The supplied policy establishes the requested fact.",
            "evidence": [{"source_label": "S1", "quote": "Canary reporting lag must not exceed 5 seconds."}],
            "missing_information": [] if status == "sufficient" else ["The other requested fact is missing."]}


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.matches = [match()]
        self.client = Mock()
        self.response = SimpleNamespace(id="response", model="gpt-6-luna", status="completed",
                                        output_text=json.dumps(assessment()), usage=None, incomplete_details=None)
        self.client.responses.create.return_value = self.response
        self.generator = GeneratorSettings("gpt-6-luna")

    def check(self, mode="sufficiency"):
        return assess_evidence("What is Canary's lag limit?", self.matches, mode=mode,
                               client=self.client, generator=self.generator)

    def test_baseline_allows_context_without_claiming_sufficiency_or_calling_model(self):
        result = self.check("baseline")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["decision"], "unchecked")
        self.client.responses.create.assert_not_called()

    def test_threshold_uses_maximum_and_preserves_low_scoring_supporting_chunks(self):
        self.matches = [match(.1), {**match(.95), "chunk_id": "chunk-b"}]
        original = deepcopy(self.matches)
        result = self.check("threshold")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["decision"], "score_pass")
        self.assertEqual(result["maximum_score"], .95)
        self.assertEqual(self.matches, original)
        self.client.responses.create.assert_not_called()

    def test_threshold_rejects_below_boundary_and_invalid_scores(self):
        self.matches[0]["reranker_score"] = .94999
        self.assertFalse(self.check("threshold")["allowed"])
        for value in (float("nan"), float("inf"), -1, 1.1):
            with self.subTest(score=value), self.assertRaises(ValueError):
                self.matches[0]["reranker_score"] = value
                self.check("threshold")

    def test_empty_context_blocks_all_modes_without_model_calls(self):
        self.matches.clear()
        for mode in ("baseline", "threshold", "sufficiency", "threshold_sufficiency"):
            with self.subTest(mode=mode):
                self.assertFalse(self.check(mode)["allowed"])
                self.assertEqual(self.check(mode)["decision"], "no_evidence")
        self.client.responses.create.assert_not_called()

    def test_sufficiency_uses_whole_sources_strict_json_and_no_gold_or_scores(self):
        result = self.check()
        self.assertTrue(result["allowed"])
        self.client.responses.create.assert_called_once()
        request = self.client.responses.create.call_args.kwargs
        payload = json.loads(request["input"])
        self.assertEqual(payload["sources"][0]["text"], self.matches[0]["text"])
        self.assertEqual(payload["sources"][0]["label"], "S1")
        self.assertNotIn("GOLD_MUST_NOT_LEAK", request["input"])
        self.assertNotIn("reranker_score", request["input"])
        self.assertEqual(request["text"]["format"], {
            "type": "json_schema", "name": "sufficiency_v1", "strict": True, "schema": SCHEMA})
        self.assertFalse(request["store"])
        self.assertEqual(result["prompt"], request["input"])
        self.assertEqual(result["instructions"], request["instructions"])
        self.assertIsNone(result["response"]["usage"])

    def test_partial_and_insufficient_context_never_allow_generation(self):
        for status in ("partial", "insufficient"):
            with self.subTest(status=status):
                self.response.output_text = json.dumps(assessment(status))
                result = self.check()
                self.assertFalse(result["allowed"])
                self.assertEqual(result["decision"], status)

    def test_quote_line_wrapping_and_spacing_do_not_reject_valid_wording(self):
        self.matches[0]["text"] = "Canary reporting lag must not\nexceed 5 seconds."
        data = assessment()
        data["evidence"][0]["quote"] = "Canary reporting lag  must not exceed\t5 seconds."
        self.response.output_text = json.dumps(data)
        result = self.check()
        self.assertTrue(result["allowed"])
        self.assertEqual(result["quote_validation"], "source_span_v2")
        self.assertEqual(result["assessment"]["evidence"], data["evidence"])
        self.assertEqual(result["verified_evidence"][0]["quote"], self.matches[0]["text"])

    def test_bold_recovery_keeps_raw_quote_and_returns_literal_source_span(self):
        self.matches[0]["text"] = "On failure, retry the **entire transaction**, including reads."
        data = assessment()
        data["evidence"][0]["quote"] = "retry the entire transaction, including reads."
        raw = json.dumps(data)
        self.response.output_text = raw
        result = self.check()
        self.assertTrue(result["allowed"])
        self.assertEqual(result["response"]["answer"], raw)
        self.assertEqual(result["assessment"], data)
        self.assertEqual(result["verified_evidence"], [{
            "source_label": "S1", "quote": "retry the **entire transaction**, including reads."}])

    def test_initial_capitalization_recovery_returns_original_source_casing(self):
        self.matches[0]["text"] = "However, this view is not serializable."
        data = assessment()
        data["evidence"][0]["quote"] = "This view is not serializable."
        self.response.output_text = json.dumps(data)
        result = self.check()
        self.assertTrue(result["allowed"])
        self.assertEqual(result["assessment"]["evidence"], data["evidence"])
        self.assertEqual(result["verified_evidence"][0]["quote"], "this view is not serializable.")

    def test_format_recovery_rejects_changed_words_numbers_negation_and_punctuation(self):
        self.matches[0]["text"] = "Retry the **entire transaction** no more than **2** times."
        for quote in ("Retry the partial transaction no more than 2 times.",
                      "Retry the entire transaction no more than 3 times.",
                      "Retry the entire transaction more than 2 times.",
                      "Retry the entire transaction no more than 2 times!"):
            with self.subTest(quote=quote):
                data = assessment()
                data["evidence"][0]["quote"] = quote
                self.response.output_text = json.dumps(data)
                result = self.check()
                self.assertFalse(result["allowed"])
                self.assertEqual(result["decision"], "error")

    def test_case_changes_inside_sql_values_and_quoted_identifiers_are_rejected(self):
        self.matches[0]["text"] = 'SELECT * FROM "Orders" WHERE owner = \'Admin\';'
        for quote in ('SELECT * FROM "orders" WHERE owner = \'Admin\';',
                      'SELECT * FROM "Orders" WHERE owner = \'admin\';'):
            with self.subTest(quote=quote):
                data = assessment()
                data["evidence"][0]["quote"] = quote
                self.response.output_text = json.dumps(data)
                self.assertEqual(self.check()["decision"], "error")

    def test_ambiguous_format_recovery_is_rejected(self):
        self.matches[0]["text"] = "Retry the **whole transaction**. Retry the **whole transaction**."
        data = assessment()
        data["evidence"][0]["quote"] = "Retry the whole transaction."
        self.response.output_text = json.dumps(data)
        self.assertEqual(self.check()["decision"], "error")

    def test_format_recovery_cannot_drop_a_word_prefix(self):
        self.matches[0]["text"] = "You must **disallow** access."
        data = assessment()
        data["evidence"][0]["quote"] = "Allow access."
        self.response.output_text = json.dumps(data)
        self.assertEqual(self.check()["decision"], "error")

    def test_format_recovery_cannot_borrow_a_quote_from_another_source(self):
        self.matches[0]["text"] = "Atlas limit is **5** seconds."
        self.matches.append({**match(), "chunk_id": "boreal", "text": "Boreal limit is **8** seconds."})
        data = assessment()
        data["evidence"][0]["quote"] = "Boreal limit is 8 seconds."
        self.response.output_text = json.dumps(data)
        self.assertEqual(self.check()["decision"], "error")

    def test_whitespace_tolerance_never_accepts_changed_words_numbers_or_punctuation(self):
        for quote in ("Canary reporting lag must exceed 5 seconds.",
                      "Canary reporting lag must not exceed 8 seconds.",
                      "Harbor reporting lag must not exceed 5 seconds.",
                      "Canary reporting lag must not exceed 5 seconds!"):
            with self.subTest(quote=quote):
                data = assessment()
                data["evidence"][0]["quote"] = quote
                self.response.output_text = json.dumps(data)
                result = self.check()
                self.assertFalse(result["allowed"])
                self.assertEqual(result["decision"], "error")

    def test_unrecognized_sources_and_fabricated_quotes_are_operational_errors(self):
        for item in ({"source_label": "S9", "quote": "5 seconds"},
                     {"source_label": "S1", "quote": "Harbor reporting lag is 5 seconds."},
                     {"source_label": "S1", "quote": ""}):
            with self.subTest(item=item):
                data = assessment()
                data["evidence"] = [item]
                self.response.output_text = json.dumps(data)
                result = self.check()
                self.assertFalse(result["allowed"])
                self.assertEqual(result["decision"], "error")
                self.assertEqual(result["response"]["answer"], self.response.output_text)

    def test_missing_evidence_and_contradictory_assessments_fail_closed(self):
        variants = [None, [], {}, {**assessment(), "extra": True},
                    {**assessment(), "evidence": []}, {**assessment(), "evidence": "S1"},
                    {**assessment(), "missing_information": ["A requested fact is missing."]},
                    {**assessment("partial"), "missing_information": []},
                    {**assessment("insufficient"), "missing_information": [""]}]
        for data in variants:
            with self.subTest(data=data):
                self.response.output_text = json.dumps(data)
                result = self.check()
                self.assertFalse(result["allowed"])
                self.assertEqual(result["decision"], "error")

    def test_incomplete_empty_and_malformed_responses_preserve_failure_and_usage(self):
        usage = {"input_tokens": 30, "output_tokens": 5, "total_tokens": 35}
        self.response.usage = Mock()
        self.response.usage.model_dump.return_value = usage
        for status, text in (("incomplete", json.dumps(assessment())), ("completed", " "),
                             ("completed", "not JSON")):
            with self.subTest(status=status, text=text):
                self.response.status, self.response.output_text = status, text
                if status == "incomplete":
                    self.response.incomplete_details = SimpleNamespace(reason="max_output_tokens")
                result = self.check()
                self.assertFalse(result["allowed"])
                self.assertEqual(result["decision"], "error")
                self.assertEqual(result["response"]["usage"], usage)

    def test_invalid_mode_or_missing_client_fails_before_paid_request(self):
        with self.assertRaises(ValueError):
            self.check("unknown")
        with self.assertRaises(ValueError):
            assess_evidence("Question", self.matches, mode="sufficiency")
        self.client.responses.create.assert_not_called()

    def test_combined_rejects_below_threshold_without_client_or_generator(self):
        self.matches[0]["reranker_score"] = .94
        result = self.check("threshold_sufficiency")
        self.assertFalse(result["allowed"])
        self.assertEqual(result["decision"], "score_reject")
        self.assertFalse(result["gate"]["allowed"])
        self.assertFalse(result["checker_called"])
        self.assertNotIn("response", result)
        self.client.responses.create.assert_not_called()
        self.assertEqual(assess_evidence("Question", self.matches, mode="threshold_sufficiency"), result)

    def test_combined_boundary_calls_checker_once_with_all_five_whole_chunks(self):
        self.matches = [{**match(.95 if i == 0 else .1), "chunk_id": f"chunk-{i}"} for i in range(5)]
        original = deepcopy(self.matches)
        result = self.check("threshold_sufficiency")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["decision"], "sufficient")
        self.assertEqual(result["gate"]["maximum_score"], .95)
        self.assertTrue(result["gate"]["allowed"])
        self.assertTrue(result["checker_called"])
        self.client.responses.create.assert_called_once()
        payload = json.loads(self.client.responses.create.call_args.kwargs["input"])
        self.assertEqual([s["text"] for s in payload["sources"]], [m["text"] for m in original])
        self.assertEqual(len(payload["sources"]), 5)
        self.assertEqual(self.matches, original)

    def test_combined_gate_pass_never_overrides_partial_or_insufficient_decision(self):
        for status in ("partial", "insufficient"):
            with self.subTest(status=status):
                self.response.output_text = json.dumps(assessment(status))
                result = self.check("threshold_sufficiency")
                self.assertTrue(result["gate"]["allowed"])
                self.assertTrue(result["checker_called"])
                self.assertFalse(result["allowed"])
                self.assertEqual(result["decision"], status)
        self.assertEqual(self.client.responses.create.call_count, 2)

    def test_combined_gate_pass_still_blocks_invalid_checker_output(self):
        for output in ("not JSON", json.dumps({**assessment(), "evidence": [
                {"source_label": "S1", "quote": "Canary limit is 8 seconds."}]})):
            with self.subTest(output=output):
                self.response.output_text = output
                result = self.check("threshold_sufficiency")
                self.assertTrue(result["gate"]["allowed"])
                self.assertTrue(result["checker_called"])
                self.assertFalse(result["allowed"])
                self.assertEqual(result["decision"], "error")
                self.assertEqual(result["response"]["answer"], output)

    def test_combined_gate_pass_requires_client_before_any_model_call(self):
        with self.assertRaises(ValueError):
            assess_evidence("Question", self.matches, mode="threshold_sufficiency")
        self.client.responses.create.assert_not_called()

    def test_enhanced_combined_context_obeys_checker_result_after_passing_gate(self):
        self.response.output_text = json.dumps(assessment("partial"))
        with patch("rag_workflow_lab.workflows.enhanced.retrieve_reranked", return_value=self.matches):
            result = prepare_context(None, None, "index", "Question", Mock(),
                                     mode="threshold_sufficiency", client=self.client, generator=self.generator)
        self.assertEqual(result["context"], [])
        self.assertEqual(result["retrieved_chunks"], self.matches)
        self.assertEqual(result["evidence_check"]["decision"], "partial")
        self.client.responses.create.assert_called_once()


class EnhancedContextTests(unittest.TestCase):
    def test_combined_context_gate_skips_checker_without_api_resources(self):
        matches = [match(.94)]
        with patch("rag_workflow_lab.workflows.enhanced.retrieve_reranked", return_value=matches):
            result = prepare_context(None, None, "index", "Question", Mock(), mode="threshold_sufficiency")
        self.assertEqual(result["context"], [])
        self.assertEqual(result["retrieved_chunks"], matches)
        self.assertFalse(result["evidence_check"]["checker_called"])

    def test_rejected_context_is_empty_but_retrieved_chunks_remain_inspectable(self):
        matches = [match(.9)]
        with patch("rag_workflow_lab.workflows.enhanced.retrieve_reranked", return_value=matches) as retrieve:
            result = prepare_context(None, None, "index", "Question", Mock(), mode="threshold")
        retrieve.assert_called_once()
        self.assertEqual(result["context"], [])
        self.assertEqual(result["retrieved_chunks"], matches)
        self.assertFalse(result["evidence_check"]["allowed"])

    def test_allowed_context_keeps_all_selected_chunks_including_low_scores(self):
        matches = [match(.99), {**match(.1), "chunk_id": "supporting-chunk"}]
        with patch("rag_workflow_lab.workflows.enhanced.retrieve_reranked", return_value=matches):
            result = prepare_context(None, None, "index", "Question", Mock(), mode="threshold")
        self.assertEqual(result["context"], matches)

    def test_invalid_mode_does_not_start_retrieval_or_reranking(self):
        with patch("rag_workflow_lab.workflows.enhanced.retrieve_reranked") as retrieve:
            with self.assertRaises(ValueError):
                prepare_context(None, None, "index", "Question", Mock(), mode="invalid")
        retrieve.assert_not_called()
