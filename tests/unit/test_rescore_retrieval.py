"""Verify annotation-only rescoring without a model, database or local corpus."""

from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

from scripts.check_retrieval import CUTOFFS, MEASUREMENT_VERSION, measure_evidence, summarize
from scripts.rescore_retrieval import rescore


class RescoreRetrievalTests(TestCase):
    def setUp(self):
        question = {"question_id": "P01", "question": "How is a plan inspected?",
                    "question_type": "direct_document", "answerability": "answerable",
                    "primary_bucket": "PG01", "scenario_family_id": "plan-inspection",
                    "evidence": [{"evidence_id": "P01-E1", "chunk_id": "definition"}],
                    "answer_requirements": [{"requirement_id": "P01-R1", "statement": "Use EXPLAIN.",
                        "support_mode": "any", "supporting_evidence_ids": ["P01-E1"]}]}
        negative = {**deepcopy(question), "question_id": "P19", "question": "What is Boreal's limit?",
                    "question_type": "insufficient_evidence", "answerability": "unanswerable",
                    "evidence": [], "answer_requirements": [{"requirement_id": "P19-R1",
                        "statement": "Insufficient evidence.", "support_mode": "corpus_scope",
                        "supporting_evidence_ids": []}], "unanswerability": {"target_entity": "Boreal"}}
        self.original = {"dataset_id": "fixture", "dataset_version": "1.7.0",
                         "source_state": {"sources": ["pinned"]}, "questions": [question, negative]}
        ranking = [{"chunk_id": "procedure", "distance": .1}, {"chunk_id": "definition", "distance": .2}]
        records = []
        for q in self.original["questions"]:
            evidence = {e["evidence_id"]: 2 for e in q["evidence"]}
            records.append({**{k:q[k] for k in ("question_id", "question", "question_type", "answerability",
                                                 "primary_bucket", "scenario_family_id")},
                "positive_evidence_applicable": bool(evidence), "unanswerability": q.get("unanswerability"),
                "evidence_ranks": evidence, "evidence_hits_at_k": {str(k):list(evidence) for k in CUTOFFS},
                "query_input_sha256": "unchanged-query", "returned_chunks": 2, "elapsed_seconds": .031,
                "ranking": deepcopy(ranking), **measure_evidence(q, {"procedure": 1, "definition": 2})})
        self.report = {"schema_version": 4, "measurement_version": MEASUREMENT_VERSION,
                       "cutoffs": list(CUTOFFS), "dataset": {"dataset_id": "fixture", "dataset_version": "1.7.0"},
                       "questions": records, "summary": summarize(records)}
        self.revised = deepcopy(self.original)
        self.revised["dataset_version"] = "1.8.0"

    def test_identical_annotations_reproduce_every_original_score(self):
        result = rescore(self.report, self.original, self.revised)
        self.assertEqual(result["questions"], self.report["questions"])
        self.assertEqual(result["summary"], self.report["summary"])

    def test_alternative_improves_first_hit_without_changing_retrieval(self):
        question = self.revised["questions"][0]
        question["evidence"].append({"evidence_id": "P01-E2", "chunk_id": "procedure"})
        question["answer_requirements"][0]["supporting_evidence_ids"].append("P01-E2")
        before = deepcopy(self.report)
        with patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")):
            for method in ("dense", "full-text", "hybrid"):
                self.report["method"] = method
                result = rescore(self.report, self.original, self.revised)
                row = result["questions"][0]
                self.assertEqual(row["reciprocal_rank_at_k"]["5"], 1)
                for field in ("ranking", "elapsed_seconds", "query_input_sha256", "returned_chunks"):
                    self.assertEqual(row[field], before["questions"][0][field])
                self.assertEqual(result["questions"][1], before["questions"][1])
        self.report.pop("method")
        self.assertEqual(self.report, before)

    def test_all_mode_still_needs_every_complementary_chunk(self):
        question = self.revised["questions"][0]
        question["evidence"].append({"evidence_id": "P01-E2", "chunk_id": "missing"})
        question["answer_requirements"][0].update(support_mode="all", supporting_evidence_ids=["P01-E1", "P01-E2"])
        result = rescore(self.report, self.original, self.revised)
        self.assertEqual(result["questions"][0]["requirement_coverage_at_k"]["20"], 0)
        self.assertEqual(result["questions"][0]["evidence_chunk_recall_at_k"]["20"], .5)

    def test_duplicate_evidence_does_not_double_count_a_chunk(self):
        self.revised["questions"][0]["evidence"].append({"evidence_id": "P01-E2", "chunk_id": "definition"})
        result = rescore(self.report, self.original, self.revised)
        self.assertEqual(result["questions"][0]["evidence_chunk_precision_at_k"]["5"], .2)

    def test_all_negative_summary_stays_null(self):
        for dataset in (self.original, self.revised):
            dataset["questions"] = dataset["questions"][1:]
        self.report["questions"] = self.report["questions"][1:]
        result = rescore(self.report, self.original, self.revised)
        self.assertIsNone(result["summary"]["mean_ndcg_at_k"]["5"])
        self.assertEqual(result["summary"]["answerable_questions"], 0)

    def test_rejects_changed_scope_questions_negatives_or_original_version(self):
        for defect in ("source_state", "question", "count", "negative", "version", "duplicate_rank", "schema"):
            revised, report = deepcopy(self.revised), deepcopy(self.report)
            if defect == "source_state": revised["source_state"]["sources"] = ["other"]
            elif defect == "question": revised["questions"][0]["question"] = "Changed question?"
            elif defect == "count": revised["questions"].pop()
            elif defect == "negative": revised["questions"][1]["unanswerability"]["target_entity"] = "Atlas"
            elif defect == "version": report["dataset"]["dataset_version"] = "other"
            elif defect == "duplicate_rank": report["questions"][0]["ranking"].append(report["questions"][0]["ranking"][0])
            else: report["schema_version"] = 3
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                rescore(report, self.original, revised)
