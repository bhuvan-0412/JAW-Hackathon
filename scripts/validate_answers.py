#!/usr/bin/env python3
"""
scripts/validate_answers.py — Quick CLI wrapper to validate answer submissions.

Usage:
    python scripts/validate_answers.py --submission submissions/final_submission.csv
"""

import sys
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import QUESTIONS_PATH, SAMPLE_SUBMISSION_PATH
from src.validation.validator import SubmissionValidator
from src.reporting.reporter import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description="Validate hackathon answer submission.")
    parser.add_argument("--submission", default=str(SAMPLE_SUBMISSION_PATH), help="Path to submission CSV")
    parser.add_argument("--questions", default=str(QUESTIONS_PATH), help="Path to questions.json")
    parser.add_argument("--report", help="Path to save Markdown validation report")
    args = parser.parse_args()

    validator = SubmissionValidator(questions_path=args.questions)
    res = validator.validate(args.submission)
    print(ReportGenerator.format_validation_terminal(res))

    if args.report:
        ReportGenerator.generate_validation_markdown(res, args.report)
        print(f"[*] Report saved to {args.report}")

    sys.exit(0 if res.is_valid else 1)


if __name__ == "__main__":
    main()
