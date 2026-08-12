#!/usr/bin/env python3
"""
scripts/pattern_breakdown.py — Analyzes question distributions, shapes, and answer types across question sets.
"""

import sys
import json
import collections
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import QUESTIONS_PATH, SAMPLE_QUESTIONS_PATH


def analyze_questions(q_path: Path, title: str):
    if not q_path.exists():
        print(f"  [!] {q_path.name} not found.")
        return

    with open(q_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions") or data.get("answers") or []
    total = len(questions)

    print("\n" + "=" * 65)
    print(f"  QUESTION DISTRIBUTION: {title} ({total} questions)")
    print("=" * 65)

    type_counts = collections.Counter(q.get("answer_type", "unknown") for q in questions)
    shape_counts = collections.Counter(q.get("shape", "unspecified") for q in questions)
    hops_counts = collections.Counter(str(q.get("hops", "unspecified")) for q in questions)

    print("\n  Answer Type Breakdown:")
    for t, c in type_counts.most_common():
        print(f"    * {t:15s}: {c:4d} ({c/total:.1%})")

    if any(q.get("shape") for q in questions):
        print("\n  Shape Breakdown:")
        for s, c in shape_counts.most_common():
            print(f"    * {s:25s}: {c:4d} ({c/total:.1%})")

    if any(q.get("hops") for q in questions):
        print("\n  Hops Breakdown:")
        for h, c in sorted(hops_counts.items()):
            print(f"    * {h:10s} hops: {c:4d} ({c/total:.1%})")

    print("=" * 65 + "\n")


def main():
    analyze_questions(SAMPLE_QUESTIONS_PATH, "Sample Questions (sample_questions.json)")
    analyze_questions(QUESTIONS_PATH, "Competition Questions (questions.json)")


if __name__ == "__main__":
    main()
