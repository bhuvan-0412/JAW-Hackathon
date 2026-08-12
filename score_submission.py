#!/usr/bin/env python3
"""
score_submission.py — Standalone CLI to benchmark submissions against gold answer keys.

Usage:
    python score_submission.py --submission my_submission.csv --questions sample_questions.json
    python score_submission.py --submission my_submission.csv --report EVALUATION_REPORT.md
    python score_submission.py --self-test
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import SAMPLE_QUESTIONS_PATH, REPORTS_DIR
from src.validation.validator import SubmissionValidator
from src.evaluation.benchmark import HarnessEvaluator
from src.evaluation.scorer import score_one
from src.reporting.reporter import ReportGenerator


def run_self_test() -> bool:
    cases = [
        (1_000_000_000, 1_000_000_000, 1.00),   # exact
        (1_000_000_000, 1_050_000_000, 0.95),   # 5% high
        (1_000_000_000,   950_000_000, 0.95),   # 5% low
        (1_000_000_000, 1_500_000_000, 0.50),   # 50% out
        (1_000_000_000, 2_000_000_000, 0.00),   # 100% out
        (1_000_000_000, 5_000_000_000, 0.00),   # far out, never negative
        (100, 99, 0.99),
        (5, 5, 1.00),
        (5, 4, 0.80),
        (66.67, 66.67, 1.00),
        (66.67, 0.6667, 0.01),                  # fraction instead of percent: ~1% credit
        (1_000_000_000, None, 0.00),            # unanswered
        (1_000_000_000, "not a number", 0.00),
        (0, 0, 1.00),                           # exact zero
        (0, 5, 0.00),                           # got non-zero when zero expected
    ]

    bad = [(g, x, e, round(score_one(g, x), 4)) for g, x, e in cases
           if abs(score_one(g, x) - e) > 5e-3]
    for g, x, e, s in bad:
        print(f"  FAIL gold={g} answered={x} expected={e} got={s}")

    passed = len(cases) - len(bad)
    print(f"Self-test: {passed}/{len(cases)} cases passed.")
    return len(bad) == 0


def main():
    parser = argparse.ArgumentParser(description="Score and benchmark hackathon submission.")
    parser.add_argument("--submission", help="Path to submission CSV (question_id,answer)")
    parser.add_argument("--questions", default=str(SAMPLE_QUESTIONS_PATH), help="Path to answer key / sample_questions.json")
    parser.add_argument("--report", help="Path to export Markdown benchmark report")
    parser.add_argument("--per-question", action="store_true", help="Print per-question score breakdown")
    parser.add_argument("--self-test", action="store_true", help="Run scoring formula self-test")
    args = parser.parse_args()

    if args.self_test:
        success = run_self_test()
        sys.exit(0 if success else 1)

    if not args.submission:
        parser.error("--submission is required unless --self-test is specified.")

    validator = SubmissionValidator(questions_path=args.questions)
    parsed_dict, _, _ = validator.load_submission_csv(args.submission)

    evaluator = HarnessEvaluator(questions_path=args.questions)
    rep = evaluator.evaluate(parsed_dict)

    if args.per_question:
        print("\n--- Per-Question Detail ---")
        for r in rep.rows:
            got_str = f"{r.got:,.2f}" if r.got is not None else "None"
            print(f"  {r.score:.3f} | {r.qid:12s} | gold={r.gold:14,.2f} | got={got_str:>14s} | err={r.error_pct:5.1f}%")

    print(ReportGenerator.format_benchmark_terminal(rep))

    if args.report:
        rep_path = Path(args.report)
        ReportGenerator.generate_benchmark_markdown(rep, rep_path)
        print(f"[*] Benchmark report saved to: {rep_path}")

    sys.exit(0)


if __name__ == "__main__":
    main()
