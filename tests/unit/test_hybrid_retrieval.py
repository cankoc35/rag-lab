"""Equal-weight RRF and bounded orchestration checks without models or a database."""

from copy import deepcopy
import unittest
from unittest.mock import Mock, patch

from rag_workflow_lab.retrieval import reciprocal_rank_fusion, retrieve_hybrid


class RankFusionTests(unittest.TestCase):
    def test_known_scores_merge_overlap_and_keep_single_method_candidates(self):
        dense = [{"chunk_id": name, "distance": score} for name, score in (("A", .1), ("B", .2), ("C", .3))]
        text = [{"chunk_id": name, "text_score": score} for name, score in (("B", 9), ("D", 8), ("A", 7))]
        before = deepcopy((dense, text))
        results = reciprocal_rank_fusion(dense, text)
        self.assertEqual([item["chunk_id"] for item in results], ["B", "A", "D", "C"])
        for item, expected in zip(results, (1/62 + 1/61, 1/61 + 1/63, 1/62, 1/63)):
            self.assertAlmostEqual(item["rrf_score"], expected)
        self.assertEqual((results[0]["dense_rank"], results[0]["full_text_rank"]), (2, 1))
        self.assertEqual((results[0]["distance"], results[0]["text_score"]), (.2, 9))
        self.assertIsNone(results[2]["dense_rank"])
        self.assertIsNone(results[2]["distance"])
        self.assertIsNone(results[3]["full_text_rank"])
        self.assertIsNone(results[3]["text_score"])
        self.assertEqual((dense, text), before)

    def test_only_rank_positions_affect_scores_and_weights_are_equal(self):
        dense = [{"chunk_id": "A", "distance": .99}, {"chunk_id": "B", "distance": 1.8}]
        text = [{"chunk_id": "B", "text_score": 1000}, {"chunk_id": "A", "text_score": .001}]
        first = reciprocal_rank_fusion(dense, text)
        self.assertEqual(first[0]["rrf_score"], first[1]["rrf_score"])
        self.assertEqual([item["chunk_id"] for item in first], ["A", "B"])
        dense[0]["distance"], text[0]["text_score"] = 0, .00001
        self.assertEqual([item["rrf_score"] for item in reciprocal_rank_fusion(dense, text)],
                         [item["rrf_score"] for item in first])

    def test_empty_lists_and_distinct_ids_with_identical_text_are_preserved(self):
        dense = [{"chunk_id": "A", "text": "Same text", "distance": .1}]
        text = [{"chunk_id": "B", "text": "Same text", "text_score": 1}]
        self.assertEqual(reciprocal_rank_fusion([], []), [])
        self.assertEqual(len(reciprocal_rank_fusion(dense, [])), 1)
        self.assertEqual(len(reciprocal_rank_fusion([], text)), 1)
        self.assertEqual([item["chunk_id"] for item in reciprocal_rank_fusion(dense, text)], ["A", "B"])

    def test_source_fields_survive_deduplication(self):
        source = {"chunk_id": "A", "snapshot_id": "v1", "source_id": "policy", "text": "Rule",
                  "title": "Policy", "url": "https://example.org", "metadata": {"anchors": ["lag"]}}
        result = reciprocal_rank_fusion([{**source, "distance": .1}], [{**source, "text_score": 2}])
        self.assertEqual(len(result), 1)
        for key, value in source.items():
            self.assertEqual(result[0][key], value)


class HybridRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.connection, self.embedder = Mock(), Mock()
        self.dense = self.enterContext(patch("rag_workflow_lab.retrieval.retrieve", return_value=[
            {"chunk_id": "A", "distance": .1}, {"chunk_id": "B", "distance": .2}]))
        self.text = self.enterContext(patch("rag_workflow_lab.retrieval.search_chunks_full_text", return_value=[
            {"chunk_id": "B", "text_score": 5}]))

    def test_same_raw_question_and_index_reach_both_bounded_searches(self):
        result = retrieve_hybrid(self.connection, self.embedder, "index", "Which rule applies?", limit=1)
        self.dense.assert_called_once_with(self.connection, self.embedder, "index", "Which rule applies?", limit=20)
        self.text.assert_called_once_with(self.connection, "index", "Which rule applies?", limit=20)
        self.assertEqual([item["chunk_id"] for item in result], ["B"])
        self.connection.commit.assert_not_called()

    def test_dense_compatibility_failure_stops_before_full_text(self):
        self.dense.side_effect = ValueError("Unknown embedding index")
        with self.assertRaisesRegex(ValueError, "Unknown"):
            retrieve_hybrid(self.connection, self.embedder, "wrong", "Question?")
        self.text.assert_not_called()

    def test_nonpositive_limits_fail_before_search(self):
        for limit in (0, -1):
            with self.subTest(limit=limit), self.assertRaisesRegex(ValueError, "limit"):
                retrieve_hybrid(self.connection, self.embedder, "index", "Question?", limit=limit)
        self.dense.assert_not_called()
        self.text.assert_not_called()


if __name__ == "__main__":
    unittest.main()
