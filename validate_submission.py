#!/usr/bin/env python3
"""
validate_submission.py — Standalone CLI to validate and audit submission CSV files.

Usage:
    python validate_submission.py --submission my_submission.csv
    python validate_submission.py --submission my_submission.csv --fix-out cleaned_submission.csv
    python validate_submission.py --submission my_submission.csv --report VALIDATION_REPORT.md
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import QUESTIONS_PATH, REPORTS_DIR
from src.validation.validator import SubmissionValidator
from src.reporting.reporter import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description="Validate hackathon submission CSV file.")
    parser.add_argument("--submission", required=True, help="Path to submission CSV (question_id,answer)")
    parser.add_argument("--questions", default=str(QUESTIONS_PATH), help="Path to questions.json")
    parser.add_argument("--fix-out", help="Path to export auto-repaired and sanitized CSV")
    parser.add_argument("--report", help="Path to export Markdown validation report")
    parser.add_argument("--quiet", action="store_true", help="Suppress terminal output")
    args = parser.parse_args()

    validator = SubmissionValidator(questions_path=args.questions)

    # If repair output requested
    if args.fix_out:
        cleaned, repairs = validator.sanitize_and_repair(
            args.submission,
            output_csv_path=args.fix_out,
            auto_rescale_percent=True,
            fill_missing=True
        )
        print(f"[*] Repaired submission saved to: {args.fix_out} ({len(repairs)} repairs applied)")
        target_to_validate = args.fix_out
    else:
        target_to_validate = args.submission

    res = validator.validate(target_to_validate)

    if not args.quiet:
        print(ReportGenerator.format_validation_terminal(res))

    if args.report:
        rep_path = Path(args.report)
        ReportGenerator.generate_validation_markdown(res, rep_path)
        print(f"[*] Validation report saved to: {rep_path}")

    sys.exit(0 if res.is_valid else 1)


if __name__ == "__main__":
    main()
