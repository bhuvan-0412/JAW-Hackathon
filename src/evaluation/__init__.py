"""
Evaluation package for scoring, benchmarking, and differential comparison.
"""

from .scorer import score_one, calculate_total_score
from .benchmark import HarnessEvaluator, BenchmarkReport, QuestionEvalRow
from .comparator import SubmissionComparator, DiffReport, QuestionDiff

__all__ = [
    "score_one",
    "calculate_total_score",
    "HarnessEvaluator",
    "BenchmarkReport",
    "QuestionEvalRow",
    "SubmissionComparator",
    "DiffReport",
    "QuestionDiff",
]
