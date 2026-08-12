"""
src/evaluation/scorer.py — Official continuous scoring formula and math utilities.
Matches evaluate.py exact specification.
"""

from typing import Optional, Union, Tuple, Any
import math


def score_one(gold: Any, got: Any) -> float:
    """
    Proportional credit for closeness according to hackathon rules:
        score = max(0.0, 1.0 - |got - gold| / |gold|)

    - Exact answer scores 1.0
    - 5% off scores 0.95
    - 50% off scores 0.50
    - 100% off or worse scores 0.0
    - Missing, None, NaN, or non-numeric answers score 0.0
    - If gold == 0: scores 1.0 if got == 0 else 0.0
    """
    if got is None or gold is None:
        return 0.0
    try:
        gold_f = float(gold)
        got_f = float(got)
    except (TypeError, ValueError):
        return 0.0

    if math.isnan(gold_f) or math.isnan(got_f) or math.isinf(gold_f) or math.isinf(got_f):
        return 0.0

    if gold_f == 0.0:
        return 1.0 if got_f == 0.0 else 0.0

    err = abs(got_f - gold_f) / abs(gold_f)
    return max(0.0, 1.0 - err)


def calculate_total_score(gold_dict: dict, submitted_dict: dict) -> Tuple[float, float, int]:
    """
    Computes total raw score sum, average score percentage (0-100%), and count of questions.
    Returns (raw_sum, avg_percent, n_questions).
    """
    if not gold_dict:
        return 0.0, 0.0, 0
    total_score = 0.0
    for qid, gold in gold_dict.items():
        got = submitted_dict.get(qid)
        total_score += score_one(gold, got)
    n = len(gold_dict)
    avg_pct = (total_score / n) * 100.0 if n > 0 else 0.0
    return total_score, avg_pct, n
