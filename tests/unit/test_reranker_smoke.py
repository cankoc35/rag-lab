"""Verify Qwen scorer math and input boundaries without model dependencies."""

import math
import unittest
from unittest.mock import Mock

from scripts.reranker_smoke import pair_tokens, yes_probability


class RerankerSmokeTests(unittest.TestCase):
    def test_yes_no_scores_are_stable_and_ordered(self):
        self.assertEqual(yes_probability(0, 0), .5)
        self.assertEqual(yes_probability(10000, -10000), 1)
        self.assertEqual(yes_probability(-10000, 10000), 0)
        self.assertAlmostEqual(yes_probability(3, 1), 1 / (1 + math.exp(-2)))

    def test_nonfinite_logits_are_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                yes_probability(value, 0)

    def test_model_template_gets_raw_text_without_truncation(self):
        tokenizer = Mock()
        tokenizer.apply_chat_template.return_value = [1, 2, 3]
        self.assertEqual(pair_tokens(tokenizer, "Question?", "Whole SQL block", "Instruction"), [1, 2, 3])
        tokenizer.apply_chat_template.assert_called_once_with([
            {"role": "system", "content": "Instruction"},
            {"role": "query", "content": "Question?"},
            {"role": "document", "content": "Whole SQL block"},
        ], tokenize=True, add_generation_prompt=False, truncation=False, return_dict=False)
