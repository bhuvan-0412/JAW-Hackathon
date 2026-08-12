#!/usr/bin/env python3
"""
compare_submissions.py — Compare two submission CSV files to detect improvements and regressions.

Usage:
    python compare_submissions.py --baseline sub_v1.csv --candidate sub_v2.csv
    python compare_submissions.py --baseline sub_v1.csv --candidate sub_v2.csv --questions sample_questions.json
"""

import sys
import argparse
import json
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.validation.validator import SubmissionValidator
from src.evaluation.comparator import SubmissionComparator


def main():
    parser = argparse.ArgumentParser(description="Compare two hackathon submissions.")
    parser.add_argument("--baseline", required=True, help="Baseline submission CSV")
    parser.add_argument("--candidate", required=True, help="Candidate submission CSV")
    parser.add_argument("--questions", help="Optional path to questions / answer key for delta score calculation")
    parser.add_argument("--report", help="Optional path to export Markdown diff report")
    args = parser.parse_args()

    validator = SubmissionValidator()
    base_dict, _, _ = validator.load_submission_csv(args.baseline)
    cand_dict, _, _ = validator.load_submission_csv(args.candidate)

    gold_dict = None
    if args.questions:
        with open(args.questions, "r", encoding="utf-8") as f:
            q_data = json.load(f)
        q_list = q_data.get("questions") or q_data.get("answers") or []
        gold_dict = {q["qid"]: float(q["answer"]) for q in q_list if "answer" in q}

    diff_report = SubmissionComparator.compare(base_dict, cand_dict, gold_dict=gold_dict)

    print("\n" + "=" * 65)
    print("  SUBMISSION COMPARISON SUMMARY")
    print("=" * 65)
    print(f"  Total Questions:   {diff_report.total_questions}")
    print(f"  Identical Answers: {diff_report.identical_count}")
    print(f"  Changed Answers:   {diff_report.changed_count}")

    if gold_dict:
        print(f"  Improved Answers:  {diff_report.improved_count} (🟢)")
        print(f"  Regressed Answers: {diff_report.regressed_count} (🔴)")
        print(f"  Baseline Total:    {diff_report.baseline_total_score:.2f}")
        print(f"  Candidate Total:   {diff_report.candidate_total_score:.2f}")
        net_str = f"+{diff_report.net_score_delta:.2f}" if diff_report.net_score_delta >= 0 else f"{diff_report.net_score_delta:.2f}"
        print(f"  Net Delta Score:   {net_str}")

    print("\n  Top Changed Questions:")
    changed_diffs = [d for d in diff_report.diffs if d.status != "UNCHANGED"][:15]
    for d in changed_diffs:
        status_tag = f"[{d.status}]"
        print(f"    * {d.qid:12s} {status_tag:12s} base={str(d.baseline_val):>12s} -> cand={str(d.candidate_val):>12s}")

    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
