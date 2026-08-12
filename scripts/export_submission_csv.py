#!/usr/bin/env python3
"""
scripts/export_submission_csv.py — Exports a validated, cleaned, bounds-enforced submission CSV.

Usage:
    python scripts/export_submission_csv.py --input raw_answers.json --out submissions/final_submission.csv
"""

import sys
import json
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import QUESTIONS_PATH, OUTPUTS_DIR
from src.validation.validator import SubmissionValidator
from src.reporting.reporter import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description="Export sanitized submission CSV.")
    parser.add_argument("--input", help="Path to input JSON or CSV answers")
    parser.add_argument("--out", default=str(OUTPUTS_DIR / "final_submission.csv"), help="Output CSV path")
    parser.add_argument("--questions", default=str(QUESTIONS_PATH), help="Path to questions.json")
    args = parser.parse_args()

    validator = SubmissionValidator(questions_path=args.questions)

    input_data = {}
    if args.input:
        in_p = Path(args.input)
        if in_p.suffix == ".json":
            with open(in_p, "r", encoding="utf-8") as f:
                input_data = json.load(f)
        else:
            input_data, _, _ = validator.load_submission_csv(in_p)
    else:
        # Generate baseline answers if no input provided
        from src.reference_engine.baseline_solver import BaselineSolver
        solver = BaselineSolver()
        with open(args.questions, "r", encoding="utf-8") as f:
            q_data = json.load(f)
        for q in q_data.get("questions", []):
            qid = q.get("qid")
            if qid:
                input_data[qid] = solver.solve_question(q)

    out_p = Path(args.out)
    cleaned, repairs = validator.sanitize_and_repair(
        input_data,
        output_csv_path=out_p,
        auto_rescale_percent=True,
        fill_missing=True
    )

    res = validator.validate(out_p)
    print(ReportGenerator.format_validation_terminal(res))
    print(f"[*] Successfully exported {len(cleaned)} validated rows to {out_p}")
    sys.exit(0 if res.is_valid else 1)


if __name__ == "__main__":
    main()
