#!/usr/bin/env python3
"""
scripts/run_sample_score.py — Executes baseline solver against sample_questions.json and evaluates score.

Usage:
    python scripts/run_sample_score.py
    python scripts/run_sample_score.py --per-question
"""

import sys
import json
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import SAMPLE_QUESTIONS_PATH, REPORTS_DIR
from src.reference_engine.baseline_solver import BaselineSolver
from src.evaluation.benchmark import HarnessEvaluator
from src.reporting.reporter import ReportGenerator


def main():
    parser = argparse.ArgumentParser(description="Evaluate baseline solver against sample questions.")
    parser.add_argument("--questions", default=str(SAMPLE_QUESTIONS_PATH), help="Path to sample_questions.json")
    parser.add_argument("--per-question", action="store_true", help="Print per-question score breakdown")
    parser.add_argument("--report", default=str(REPORTS_DIR / "EVALUATION_REPORT.md"), help="Path to output markdown report")
    args = parser.parse_args()

    q_path = Path(args.questions)
    if not q_path.exists():
        print(f"Error: {q_path} not found.")
        sys.exit(1)

    with open(q_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    questions = data.get("questions") or []

    print(f"[*] Solving {len(questions)} sample questions with BaselineSolver...")
    solver = BaselineSolver()
    answers = {}
    for q in questions:
        qid = q.get("qid")
        if qid:
            answers[qid] = solver.solve_question(q)

    evaluator = HarnessEvaluator(q_path)
    rep = evaluator.evaluate(answers)

    if args.per_question:
        print("\n--- Per-Question Breakdown ---")
        for r in rep.rows:
            got_str = f"{r.got:,.2f}" if r.got is not None else "None"
            print(f"  Score: {r.score:.3f} | {r.qid:12s} | Gold: {r.gold:14,.2f} | Got: {got_str:>14s} | {r.shape}")

    print(ReportGenerator.format_benchmark_terminal(rep))

    if args.report:
        ReportGenerator.generate_benchmark_markdown(rep, args.report)
        print(f"[*] Benchmark report saved to {args.report}")

    sys.exit(0)


if __name__ == "__main__":
    main()
