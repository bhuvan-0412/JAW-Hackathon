"""
tests/test_comparator.py — Unit tests for submission diff tool and regression tracking.
"""

import unittest
from src.evaluation.comparator import SubmissionComparator


class TestComparator(unittest.TestCase):

    def test_compare_without_gold(self):
        base = {"Q1": 100, "Q2": 200, "Q3": 300}
        cand = {"Q1": 100, "Q2": 250, "Q3": 300}
        rep = SubmissionComparator.compare(base, cand)

        self.assertEqual(rep.total_questions, 3)
        self.assertEqual(rep.identical_count, 2)
        self.assertEqual(rep.changed_count, 1)

    def test_compare_with_gold(self):
        gold = {"Q1": 100, "Q2": 200, "Q3": 300}
        base = {"Q1": 80,  "Q2": 200, "Q3": 0}    # scores: 0.80, 1.00, 0.00 -> 1.80
        cand = {"Q1": 100, "Q2": 150, "Q3": 300}  # scores: 1.00, 0.75, 1.00 -> 2.75

        rep = SubmissionComparator.compare(base, cand, gold_dict=gold)
        self.assertEqual(rep.improved_count, 2)   # Q1, Q3 improved
        self.assertEqual(rep.regressed_count, 1)  # Q2 regressed
        self.assertAlmostEqual(rep.baseline_total_score, 1.80, places=2)
        self.assertAlmostEqual(rep.candidate_total_score, 2.75, places=2)
        self.assertAlmostEqual(rep.net_score_delta, 0.95, places=2)


if __name__ == "__main__":
    unittest.main()
