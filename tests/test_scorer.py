"""
tests/test_scorer.py — Unit tests for evaluation scoring and benchmark metrics.
"""

import unittest
from src.evaluation.scorer import score_one, calculate_total_score
from src.evaluation.benchmark import HarnessEvaluator
from src.config import SAMPLE_QUESTIONS_PATH


class TestScorer(unittest.TestCase):

    def test_score_one_exact(self):
        self.assertEqual(score_one(1_000, 1_000), 1.0)
        self.assertEqual(score_one(50.25, 50.25), 1.0)
        self.assertEqual(score_one(0, 0), 1.0)

    def test_score_one_proportional(self):
        # 5% error -> 0.95
        self.assertAlmostEqual(score_one(100, 105), 0.95, places=4)
        self.assertAlmostEqual(score_one(100, 95), 0.95, places=4)
        # 50% error -> 0.50
        self.assertAlmostEqual(score_one(100, 150), 0.50, places=4)
        # 100% error -> 0.00
        self.assertEqual(score_one(100, 200), 0.0)
        # >100% error -> 0.00 (no negative scores)
        self.assertEqual(score_one(100, 500), 0.0)

    def test_score_one_non_numeric_and_none(self):
        self.assertEqual(score_one(100, None), 0.0)
        self.assertEqual(score_one(100, "text"), 0.0)
        self.assertEqual(score_one(None, 100), 0.0)
        self.assertEqual(score_one(float("nan"), 100), 0.0)

    def test_calculate_total_score(self):
        gold = {"Q1": 100, "Q2": 200, "Q3": 300}
        got = {"Q1": 100, "Q2": 210, "Q3": 0}  # scores: 1.0, 0.95, 0.0 -> 1.95 total
        total, avg_pct, n = calculate_total_score(gold, got)
        self.assertAlmostEqual(total, 1.95, places=4)
        self.assertEqual(n, 3)
        self.assertAlmostEqual(avg_pct, (1.95 / 3) * 100.0, places=2)


class TestBenchmarkEvaluator(unittest.TestCase):

    def test_evaluator_on_sample_questions(self):
        evaluator = HarnessEvaluator(SAMPLE_QUESTIONS_PATH)
        self.assertGreater(len(evaluator.questions_list), 0)

        # Build perfect answers
        perfect_answers = {q["qid"]: q.get("answer") for q in evaluator.questions_list if "answer" in q}
        rep = evaluator.evaluate(perfect_answers)

        self.assertEqual(rep.overall_percentage, 100.0)
        self.assertEqual(rep.error_histogram["exact (1.00)"], len(perfect_answers))
        self.assertEqual(len(rep.worst_misses), 0)


if __name__ == "__main__":
    unittest.main()
