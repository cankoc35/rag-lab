"""Keep reranking evidence-blind and preserve the fixed candidate set."""

from contextlib import redirect_stdout
from copy import deepcopy
import io
import unittest
from unittest.mock import call, patch

from scripts.reranker_probe import rerank


class RerankerProbeTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [{"chunk_id": "a", "source_id": "one", "rrf_score": .03},
                           {"chunk_id": "b", "source_id": "two", "rrf_score": .02}]
        self.chunks = {"a": {"heading_path": ["SQL", "EXPLAIN"], "text": "Complete SQL;"},
                       "b": {"heading_path": ["Backup"], "text": "Whole backup policy."}}

    def test_only_question_and_whole_documents_reach_scorer(self):
        original = deepcopy(self.candidates)
        with patch("scripts.reranker_probe.score", side_effect=[.1, .9]) as scorer, redirect_stdout(io.StringIO()):
            ranked = rerank("Raw question?", self.candidates, self.chunks, None, None, {})
        self.assertEqual([m["chunk_id"] for m in ranked], ["b", "a"])
        self.assertEqual([m["rrf_rank"] for m in ranked], [2, 1])
        self.assertEqual([m["source_id"] for m in ranked], ["two", "one"])
        self.assertEqual(self.candidates, original)
        self.assertEqual(scorer.call_args_list, [
            call(None, None, "Raw question?", "SQL > EXPLAIN\n\nComplete SQL;", {}),
            call(None, None, "Raw question?", "Backup\n\nWhole backup policy.", {}),
        ])

    def test_equal_scores_preserve_original_rrf_order(self):
        with patch("scripts.reranker_probe.score", return_value=.5), redirect_stdout(io.StringIO()):
            ranked = rerank("Question?", self.candidates, self.chunks, None, None, {})
        self.assertEqual([m["chunk_id"] for m in ranked], ["a", "b"])

    def test_batches_preserve_every_candidate_and_handle_short_final_batch(self):
        candidates = [{"chunk_id": str(i), "source_id": "source"} for i in range(6)]
        chunks = {str(i): {"heading_path": ["SQL"], "text": f"Whole passage {i}"} for i in range(6)}
        with patch("scripts.reranker_probe.score") as single, patch(
                "scripts.reranker_probe.score_batch", side_effect=[[.1, .2, .3, .4], [.5, .6]]) as batched:
            with redirect_stdout(io.StringIO()):
                ranked = rerank("Raw question?", candidates, chunks, None, None, {}, batch_size=4)
        single.assert_not_called()
        self.assertEqual([len(c.args[3]) for c in batched.call_args_list], [4, 2])
        self.assertEqual([c.args[2] for c in batched.call_args_list], ["Raw question?"] * 2)
        self.assertEqual(batched.call_args_list[0].args[3], [f"SQL\n\nWhole passage {i}" for i in range(4)])
        self.assertEqual([m["chunk_id"] for m in ranked], ["5", "4", "3", "2", "1", "0"])
        self.assertEqual([m["rrf_rank"] for m in ranked], [6, 5, 4, 3, 2, 1])
        self.assertTrue(all(m["scoring_seconds"] is None for m in ranked))


if __name__ == "__main__":
    unittest.main()
