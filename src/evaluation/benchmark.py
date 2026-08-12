"""
src/evaluation/benchmark.py — Multi-dimensional benchmark evaluation and diagnostic engine.
"""

import json
import collections
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field, asdict

from src.config import SAMPLE_QUESTIONS_PATH
from .scorer import score_one


@dataclass
class QuestionEvalRow:
    qid: str
    shape: Optional[str]
    answer_type: Optional[str]
    hops: Optional[int]
    gold: float
    got: Optional[float]
    score: float
    error_pct: float
    residual: Optional[float]
    question_text: str = ""
    reasoning_steps: List[str] = field(default_factory=list)


@dataclass
class CategoryScore:
    category: str
    score: float
    count: int

    @property
    def percentage(self) -> float:
        return (self.score / max(self.count, 1)) * 100.0


@dataclass
class BenchmarkReport:
    total_score: float
    max_score: float
    overall_percentage: float
    total_questions: int
    answered_questions: int
    by_shape: Dict[str, CategoryScore] = field(default_factory=dict)
    by_type: Dict[str, CategoryScore] = field(default_factory=dict)
    by_hops: Dict[str, CategoryScore] = field(default_factory=dict)
    error_histogram: Dict[str, int] = field(default_factory=dict)
    rows: List[QuestionEvalRow] = field(default_factory=list)
    worst_misses: List[QuestionEvalRow] = field(default_factory=list)
    best_hits: List[QuestionEvalRow] = field(default_factory=list)


class HarnessEvaluator:
    """
    Evaluator that produces deep diagnostic benchmarks across all questions, shapes, and hops.
    """

    def __init__(self, questions_path: Union[str, Path] = SAMPLE_QUESTIONS_PATH):
        self.questions_path = Path(questions_path)
        self.questions_list = self._load_questions()

    def _load_questions(self) -> List[dict]:
        if not self.questions_path.exists():
            return []
        with open(self.questions_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("questions") or data.get("answers") or []

    def evaluate(self, submitted_dict: Dict[str, Any]) -> BenchmarkReport:
        """
        Evaluate answers against gold ground truth.
        """
        rows = []
        by_shape_accum = collections.defaultdict(lambda: [0.0, 0])
        by_type_accum = collections.defaultdict(lambda: [0.0, 0])
        by_hops_accum = collections.defaultdict(lambda: [0.0, 0])

        error_hist = {
            "exact (1.00)": 0,
            "95% - 99.9%": 0,
            "80% - 94.9%": 0,
            "50% - 79.9%": 0,
            ">0% - 49.9%": 0,
            "0% (Zero)": 0,
        }

        answered_count = 0

        for q in self.questions_list:
            if q.get("scored") is False:
                continue

            qid = q.get("qid", "")
            gold = q.get("answer", q.get("answer_gold"))
            if gold is None:
                continue

            try:
                gold_f = float(gold)
            except (ValueError, TypeError):
                continue

            got_raw = submitted_dict.get(qid)
            got_f = None
            if got_raw is not None:
                try:
                    got_f = float(str(got_raw).replace(",", "").replace("₹", "").replace("INR", "").strip())
                    answered_count += 1
                except ValueError:
                    got_f = None

            s = score_one(gold_f, got_f)

            # Error and residual
            if got_f is not None and gold_f != 0:
                err_pct = (abs(got_f - gold_f) / abs(gold_f)) * 100.0
                residual = got_f - gold_f
            else:
                err_pct = 100.0 if got_f is None else (0.0 if got_f == gold_f else 100.0)
                residual = None if got_f is None else (got_f - gold_f)

            shape = q.get("shape", "unspecified")
            ans_type = q.get("answer_type", "unspecified")
            hops = str(q.get("hops", "unspecified"))

            row = QuestionEvalRow(
                qid=qid,
                shape=shape,
                answer_type=ans_type,
                hops=q.get("hops"),
                gold=gold_f,
                got=got_f,
                score=s,
                error_pct=err_pct,
                residual=residual,
                question_text=q.get("question", ""),
                reasoning_steps=q.get("reasoning_steps", [])
            )
            rows.append(row)

            # Accumulators
            by_shape_accum[shape][0] += s
            by_shape_accum[shape][1] += 1

            by_type_accum[ans_type][0] += s
            by_type_accum[ans_type][1] += 1

            by_hops_accum[hops][0] += s
            by_hops_accum[hops][1] += 1

            # Histogram
            if s >= 0.9999:
                error_hist["exact (1.00)"] += 1
            elif s >= 0.95:
                error_hist["95% - 99.9%"] += 1
            elif s >= 0.80:
                error_hist["80% - 94.9%"] += 1
            elif s >= 0.50:
                error_hist["50% - 79.9%"] += 1
            elif s > 0.0:
                error_hist[">0% - 49.9%"] += 1
            else:
                error_hist["0% (Zero)"] += 1

        total_score = sum(r.score for r in rows)
        total_q = len(rows)
        overall_pct = (total_score / max(total_q, 1)) * 100.0

        by_shape = {
            k: CategoryScore(category=k, score=v[0], count=v[1])
            for k, v in sorted(by_shape_accum.items(), key=lambda x: -x[1][0] / max(x[1][1], 1))
        }
        by_type = {
            k: CategoryScore(category=k, score=v[0], count=v[1])
            for k, v in sorted(by_type_accum.items(), key=lambda x: -x[1][0] / max(x[1][1], 1))
        }
        by_hops = {
            k: CategoryScore(category=k, score=v[0], count=v[1])
            for k, v in sorted(by_hops_accum.items(), key=lambda x: str(x[0]))
        }

        # Sort misses and hits
        worst_misses = sorted([r for r in rows if r.score < 1.0], key=lambda x: x.score)[:10]
        best_hits = sorted([r for r in rows if r.score == 1.0], key=lambda x: x.qid)[:10]

        return BenchmarkReport(
            total_score=round(total_score, 4),
            max_score=float(total_q),
            overall_percentage=round(overall_pct, 2),
            total_questions=total_q,
            answered_questions=answered_count,
            by_shape=by_shape,
            by_type=by_type,
            by_hops=by_hops,
            error_histogram=error_hist,
            rows=rows,
            worst_misses=worst_misses,
            best_hits=best_hits
        )
