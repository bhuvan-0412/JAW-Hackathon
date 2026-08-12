#!/usr/bin/env python3
"""
scripts/update_score_history.py — Records benchmark run results to a persistent history log.
"""

import sys
import json
import datetime
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import CACHE_DIR, SAMPLE_QUESTIONS_PATH
from src.evaluation.benchmark import HarnessEvaluator
from src.validation.validator import SubmissionValidator

HISTORY_PATH = CACHE_DIR / "score_history.json"


def main():
    parser = argparse.ArgumentParser(description="Log benchmark score to history tracking.")
    parser.add_argument("--submission", required=True, help="Submission CSV path")
    parser.add_argument("--questions", default=str(SAMPLE_QUESTIONS_PATH), help="Questions key path")
    parser.add_argument("--tag", default="run", help="Identifier tag / note for the run")
    args = parser.parse_args()

    validator = SubmissionValidator(questions_path=args.questions)
    parsed, _, _ = validator.load_submission_csv(args.submission)

    evaluator = HarnessEvaluator(args.questions)
    rep = evaluator.evaluate(parsed)

    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "tag": args.tag,
        "submission_file": str(args.submission),
        "total_score": rep.total_score,
        "max_score": rep.max_score,
        "accuracy_pct": rep.overall_percentage,
        "answered_count": rep.answered_questions,
        "by_shape": {k: v.percentage for k, v in rep.by_shape.items()}
    }

    history = []
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.append(entry)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    print(f"[*] Appended score to history: {rep.total_score:.2f}/{rep.max_score:.0f} ({rep.overall_percentage:.1f}%) [Tag: {args.tag}]")
    print(f"[*] History stored at: {HISTORY_PATH}")


if __name__ == "__main__":
    main()
