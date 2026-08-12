"""
tests/test_validator.py — Unit tests for SubmissionValidator and validation rules.
"""

import unittest
from pathlib import Path
from src.validation.rules import is_valid_number, check_percent_rescale_needed, validate_single_answer
from src.validation.validator import SubmissionValidator, IssueSeverity


class TestValidationRules(unittest.TestCase):

    def test_is_valid_number(self):
        self.assertEqual(is_valid_number(123), (True, 123.0))
        self.assertEqual(is_valid_number(45.67), (True, 45.67))
        self.assertEqual(is_valid_number(" 1,000.50 "), (True, 1000.50))
        self.assertEqual(is_valid_number("INR 5,00,000"), (True, 500000.0))
        self.assertEqual(is_valid_number("₹ 250"), (True, 250.0))
        self.assertEqual(is_valid_number("85.5%"), (True, 85.5))
        self.assertEqual(is_valid_number(None), (False, None))
        self.assertEqual(is_valid_number("invalid_text"), (False, None))
        self.assertEqual(is_valid_number(float("nan")), (False, None))
        self.assertEqual(is_valid_number(float("inf")), (False, None))

    def test_check_percent_rescale_needed(self):
        self.assertTrue(check_percent_rescale_needed(0.3333))
        self.assertTrue(check_percent_rescale_needed(0.9019))
        self.assertTrue(check_percent_rescale_needed(1.0))
        self.assertFalse(check_percent_rescale_needed(33.33))
        self.assertFalse(check_percent_rescale_needed(90.19))
        self.assertFalse(check_percent_rescale_needed(0.0))

    def test_validate_single_answer_percent(self):
        # Valid percentage
        issues = validate_single_answer("Q1", 45.5, "percent")
        self.assertEqual(len(issues), 0)

        # Fraction percentage warning
        issues = validate_single_answer("Q2", 0.455, "percent")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["severity"], "WARNING")
        self.assertEqual(issues[0]["code"], "FRACTION_PERCENT_SUSPECTED")

        # Out of bounds percentage error
        issues = validate_single_answer("Q3", 150.0, "percent")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["severity"], "ERROR")
        self.assertEqual(issues[0]["code"], "OUT_OF_BOUNDS_PERCENT")

    def test_validate_single_answer_days_and_count(self):
        # Negative days error
        issues = validate_single_answer("Q4", -5, "days")
        self.assertTrue(any(i["severity"] == "ERROR" for i in issues))

        # Negative count error
        issues = validate_single_answer("Q5", -2, "count")
        self.assertTrue(any(i["severity"] == "ERROR" for i in issues))

        # Non-integer count warning
        issues = validate_single_answer("Q6", 3.7, "count")
        self.assertTrue(any(i["severity"] == "WARNING" for i in issues))


class TestSubmissionValidator(unittest.TestCase):

    def setUp(self):
        self.validator = SubmissionValidator()

    def test_validator_with_valid_dict(self):
        # Mock answers for all expected questions
        mock_answers = {}
        for qid, q in self.validator.questions_data.items():
            t = q.get("answer_type", "money")
            if t == "percent":
                mock_answers[qid] = 50.0
            elif t == "count":
                mock_answers[qid] = 3
            elif t == "days":
                mock_answers[qid] = 400
            else:
                mock_answers[qid] = 100_000_000.0

        res = self.validator.validate(mock_answers)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.valid_answers_count, len(self.validator.qids_expected))
        self.assertEqual(res.error_count, 0)

    def test_validator_with_missing_qids(self):
        incomplete_answers = {"HV-IC-0001": 1000}
        res = self.validator.validate(incomplete_answers)
        self.assertFalse(res.is_valid)
        self.assertTrue(len(res.missing_qids) > 0)
        self.assertTrue(res.error_count > 0)

    def test_sanitize_and_repair(self):
        messy_answers = {
            "HV-IC-0001": "INR 294.24 Cr",
            "HV-IC-0003": 0.9019,  # fraction percent
            "HV-IC-0006": "not_a_number",
        }
        cleaned, repairs = self.validator.sanitize_and_repair(messy_answers, fill_missing=True)
        self.assertEqual(len(cleaned), len(self.validator.qids_expected))
        self.assertGreaterEqual(len(repairs), 1)
        # Percent was rescaled
        self.assertAlmostEqual(cleaned["HV-IC-0003"], 90.19, places=2)


if __name__ == "__main__":
    unittest.main()
