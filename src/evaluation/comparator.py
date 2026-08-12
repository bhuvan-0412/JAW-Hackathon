"""
src/evaluation/comparator.py — Submission differential analyzer and regression detector.
"""

from typing import Dict, List, Optional, Union, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path

from .scorer import score_one


@dataclass
class QuestionDiff:
    qid: str
    baseline_val: Optional[float]
    candidate_val: Optional[float]
    gold_val: Optional[float] = None
    baseline_score: Optional[float] = None
    candidate_score: Optional[float] = None
    score_delta: Optional[float] = None
    status: str = "UNCHANGED"  # IMPROVED, REGRESSED, UNCHANGED, DIFFERENT, NEW, MISSING


@dataclass
class DiffReport:
    total_questions: int
    identical_count: int
    changed_count: int
    improved_count: int
    regressed_count: int
    baseline_total_score: Optional[float] = None
    candidate_total_score: Optional[float] = None
    net_score_delta: Optional[float] = None
    diffs: List[QuestionDiff] = field(default_factory=list)


class SubmissionComparator:
    """
    Compares two submission sets to track pipeline progress, detect regressions,
    and measure impact of upstream Role A/B/C changes.
    """

    @staticmethod
    def compare(
        baseline_dict: Dict[str, Any],
        candidate_dict: Dict[str, Any],
        gold_dict: Optional[Dict[str, float]] = None
    ) -> DiffReport:
        all_qids = sorted(list(set(baseline_dict.keys()) | set(candidate_dict.keys())))

        diffs = []
        identical = 0
        changed = 0
        improved = 0
        regressed = 0

        baseline_score_accum = 0.0 if gold_dict else None
        candidate_score_accum = 0.0 if gold_dict else None

        for qid in all_qids:
            b_val = baseline_dict.get(qid)
            c_val = candidate_dict.get(qid)

            try:
                b_num = float(b_val) if b_val is not None else None
            except ValueError:
                b_num = None

            try:
                c_num = float(c_val) if c_val is not None else None
            except ValueError:
                c_num = None

            gold = gold_dict.get(qid) if gold_dict else None
            b_score = score_one(gold, b_num) if gold is not None else None
            c_score = score_one(gold, c_num) if gold is not None else None
            score_delta = (c_score - b_score) if (c_score is not None and b_score is not None) else None

            if b_score is not None:
                baseline_score_accum += b_score
            if c_score is not None:
                candidate_score_accum += c_score

            status = "UNCHANGED"
            if b_num == c_num:
                identical += 1
                status = "UNCHANGED"
            else:
                changed += 1
                if score_delta is not None:
                    if score_delta > 0.0001:
                        status = "IMPROVED"
                        improved += 1
                    elif score_delta < -0.0001:
                        status = "REGRESSED"
                        regressed += 1
                    else:
                        status = "DIFFERENT"
                else:
                    status = "DIFFERENT"

            diffs.append(QuestionDiff(
                qid=qid,
                baseline_val=b_num,
                candidate_val=c_num,
                gold_val=gold,
                baseline_score=b_score,
                candidate_score=c_score,
                score_delta=score_delta,
                status=status
            ))

        net_delta = (candidate_score_accum - baseline_score_accum) if (candidate_score_accum is not None and baseline_score_accum is not None) else None

        return DiffReport(
            total_questions=len(all_qids),
            identical_count=identical,
            changed_count=changed,
            improved_count=improved,
            regressed_count=regressed,
            baseline_total_score=round(baseline_score_accum, 4) if baseline_score_accum is not None else None,
            candidate_total_score=round(candidate_score_accum, 4) if candidate_score_accum is not None else None,
            net_score_delta=round(net_delta, 4) if net_delta is not None else None,
            diffs=diffs
        )
