"""
src/validation/validator.py — Comprehensive submission validation and anomaly detection engine.
"""

import csv
import json
import enum
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from dataclasses import dataclass, field, asdict

from src.config import (
    QUESTIONS_PATH,
    SAMPLE_QUESTIONS_PATH,
    COMPANY_METADATA,
    VALIDATION_BOUNDS,
)
from .rules import validate_single_answer, is_valid_number, check_percent_rescale_needed


class IssueSeverity(str, enum.Enum):
    ERROR = "ERROR"        # Submission breaking (e.g. non-numeric, missing required QID, out of bounds)
    WARNING = "WARNING"    # Potential bug (e.g. fraction percent, extreme outlier, non-integer count)
    INFO = "INFO"          # Informational note (e.g. formatting whitespace cleaned)


@dataclass
class ValidationIssue:
    qid: str
    severity: IssueSeverity
    code: str
    message: str
    row_num: Optional[int] = None
    raw_value: Optional[str] = None


@dataclass
class ValidationResult:
    is_valid: bool
    total_questions_expected: int
    total_questions_found: int
    valid_answers_count: int
    missing_qids: List[str] = field(default_factory=list)
    unexpected_qids: List[str] = field(default_factory=list)
    duplicate_qids: List[str] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)
    type_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    anomalies: List[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)

    @property
    def pass_rate(self) -> float:
        if not self.total_questions_expected:
            return 0.0
        return (self.valid_answers_count / self.total_questions_expected) * 100.0


class SubmissionValidator:
    """
    Validates CSV submissions against official hackathon specifications,
    detects anomalies, and provides automated repair routines.
    """

    def __init__(self, questions_path: Union[str, Path] = QUESTIONS_PATH):
        self.questions_path = Path(questions_path)
        self.questions_data = self._load_questions()
        self.qids_expected = set(self.questions_data.keys())

    def _load_questions(self) -> Dict[str, dict]:
        if not self.questions_path.exists():
            return {}
        with open(self.questions_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        questions_list = data.get("questions") or data.get("answers") or []
        return {q["qid"]: q for q in questions_list if "qid" in q}

    def load_submission_csv(self, path: Union[str, Path]) -> Tuple[Dict[str, Any], List[dict], List[ValidationIssue]]:
        """
        Loads submission CSV, handles header variations, whitespace, and records row issues.
        Returns (parsed_dict, raw_rows, header_issues).
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Submission file not found: {path}")

        parsed = {}
        raw_rows = []
        issues = []

        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = list(csv.reader(f))

        if not reader:
            issues.append(ValidationIssue(
                qid="HEADER",
                severity=IssueSeverity.ERROR,
                code="EMPTY_FILE",
                message="Submission file is completely empty."
            ))
            return parsed, raw_rows, issues

        header = [h.strip().lower() for h in reader[0]]
        start_row = 1

        if "question_id" in header:
            qi = header.index("question_id")
            ai = header.index("answer") if "answer" in header else (1 if len(header) > 1 else 0)
        elif "qid" in header:
            qi = header.index("qid")
            ai = header.index("answer") if "answer" in header else (1 if len(header) > 1 else 0)
        else:
            # Fallback assuming row 0 is already data
            qi, ai = 0, 1
            start_row = 0
            issues.append(ValidationIssue(
                qid="HEADER",
                severity=IssueSeverity.WARNING,
                code="MISSING_STANDARD_HEADER",
                message="No standard 'question_id,answer' header found. Assuming column 0=qid, column 1=answer."
            ))

        seen_qids = set()
        for row_idx, row in enumerate(reader[start_row:], start=start_row + 1):
            if not row or len(row) <= max(qi, ai):
                continue
            raw_qid = row[qi].strip()
            raw_ans = row[ai].strip() if len(row) > ai else ""

            if not raw_qid:
                continue

            raw_rows.append({"row_num": row_idx, "qid": raw_qid, "raw_answer": raw_ans})

            if raw_qid in seen_qids:
                issues.append(ValidationIssue(
                    qid=raw_qid,
                    severity=IssueSeverity.WARNING,
                    code="DUPLICATE_QID_ROW",
                    message=f"Duplicate entry found for QID '{raw_qid}' at row {row_idx}.",
                    row_num=row_idx,
                    raw_value=raw_ans
                ))

            seen_qids.add(raw_qid)
            parsed[raw_qid] = raw_ans

        return parsed, raw_rows, issues

    def validate(self, submission_input: Union[str, Path, Dict[str, Any]]) -> ValidationResult:
        """
        Execute full validation checks on a CSV path or in-memory answer dictionary.
        """
        header_issues = []
        if isinstance(submission_input, (str, Path)):
            parsed_dict, raw_rows, header_issues = self.load_submission_csv(submission_input)
        elif isinstance(submission_input, dict):
            parsed_dict = {str(k).strip(): v for k, v in submission_input.items()}
            raw_rows = [{"row_num": None, "qid": k, "raw_answer": str(v)} for k, v in parsed_dict.items()]
        else:
            raise TypeError("submission_input must be a filepath or dict.")

        found_qids = set(parsed_dict.keys())
        expected_qids = self.qids_expected or found_qids

        missing_qids = sorted(list(expected_qids - found_qids))
        unexpected_qids = sorted(list(found_qids - expected_qids))

        # Check duplicate occurrences from raw_rows
        seen = set()
        duplicates = []
        for r in raw_rows:
            q = r["qid"]
            if q in seen and q not in duplicates:
                duplicates.append(q)
            seen.add(q)

        all_issues = list(header_issues)

        # Flag missing QIDs
        for mq in missing_qids:
            all_issues.append(ValidationIssue(
                qid=mq,
                severity=IssueSeverity.ERROR,
                code="MISSING_QUESTION_ID",
                message=f"Required question ID '{mq}' is absent from submission."
            ))

        # Flag unexpected QIDs
        for uq in unexpected_qids:
            all_issues.append(ValidationIssue(
                qid=uq,
                severity=IssueSeverity.WARNING,
                code="UNEXPECTED_QUESTION_ID",
                message=f"Question ID '{uq}' was not found in the official question set."
            ))

        # Validate answer values and types
        valid_answers = 0
        type_breakdown = {
            "money": {"total": 0, "valid": 0, "zeros": 0, "sum": 0.0},
            "percent": {"total": 0, "valid": 0, "zeros": 0, "sum": 0.0},
            "count": {"total": 0, "valid": 0, "zeros": 0, "sum": 0.0},
            "days": {"total": 0, "valid": 0, "zeros": 0, "sum": 0.0},
            "unknown": {"total": 0, "valid": 0, "zeros": 0, "sum": 0.0},
        }

        for qid, ans in parsed_dict.items():
            q_info = self.questions_data.get(qid, {})
            ans_type = q_info.get("answer_type", "unknown")
            if ans_type not in type_breakdown:
                type_breakdown[ans_type] = {"total": 0, "valid": 0, "zeros": 0, "sum": 0.0}

            type_breakdown[ans_type]["total"] += 1

            ans_issues = validate_single_answer(qid, ans, ans_type)
            is_valid, num_val = is_valid_number(ans)

            for iss in ans_issues:
                all_issues.append(ValidationIssue(
                    qid=qid,
                    severity=IssueSeverity(iss["severity"]),
                    code=iss["code"],
                    message=iss["message"],
                    raw_value=str(ans)
                ))

            if is_valid and not any(i.severity == IssueSeverity.ERROR for i in all_issues if i.qid == qid):
                valid_answers += 1
                type_breakdown[ans_type]["valid"] += 1
                if num_val == 0.0:
                    type_breakdown[ans_type]["zeros"] += 1
                type_breakdown[ans_type]["sum"] += num_val

        # Detect dataset-wide anomalies
        anomalies = self.detect_anomalies(parsed_dict, expected_qids)

        is_valid_overall = (
            len(missing_qids) == 0 and
            sum(1 for i in all_issues if i.severity == IssueSeverity.ERROR) == 0
        )

        return ValidationResult(
            is_valid=is_valid_overall,
            total_questions_expected=len(expected_qids),
            total_questions_found=len(found_qids),
            valid_answers_count=valid_answers,
            missing_qids=missing_qids,
            unexpected_qids=unexpected_qids,
            duplicate_qids=duplicates,
            issues=all_issues,
            type_breakdown=type_breakdown,
            anomalies=anomalies
        )

    def detect_anomalies(self, parsed_dict: Dict[str, Any], expected_qids: set) -> List[str]:
        """
        Run statistical anomaly detectors on submission values.
        """
        anomalies = []
        if not parsed_dict:
            return ["Submission contains no data rows."]

        values = []
        zero_count = 0
        fractions_in_percent = 0

        for qid, ans in parsed_dict.items():
            is_num, val = is_valid_number(ans)
            if is_num:
                values.append(val)
                if val == 0:
                    zero_count += 1
                q_info = self.questions_data.get(qid, {})
                if q_info.get("answer_type") == "percent" and check_percent_rescale_needed(val):
                    fractions_in_percent += 1

        total = len(values)
        if total == 0:
            return ["No parseable numeric values found in submission."]

        # 1. Check for all/majority identical answers
        from collections import Counter
        counts = Counter(values)
        most_common_val, most_common_freq = counts.most_common(1)[0]
        if most_common_freq >= max(15, int(total * 0.35)):
            anomalies.append(
                f"High value repetition: value '{most_common_val}' appears {most_common_freq}/{total} times ({most_common_freq/total:.1%})."
            )

        # 2. Check for excessive zero rate
        zero_rate = zero_count / total
        if zero_rate > 0.25:
            anomalies.append(
                f"High zero frequency: {zero_count}/{total} answers ({zero_rate:.1%}) are zero. Check for unhandled exceptions or dummy initializers."
            )

        # 3. Check for fraction percent systemic error
        if fractions_in_percent >= 3:
            anomalies.append(
                f"Fractional percentages detected: {fractions_in_percent} percent questions are in range (0, 1]. They should likely be scaled by 100."
            )

        return anomalies

    def sanitize_and_repair(
        self,
        submission_input: Union[str, Path, Dict[str, Any]],
        output_csv_path: Optional[Union[str, Path]] = None,
        auto_rescale_percent: bool = True,
        fill_missing: bool = True
    ) -> Tuple[Dict[str, float], List[str]]:
        """
        Produces a clean, verified submission dictionary and optional CSV file.
        Fixes formatting, strips symbols, auto-rescales fraction percentages,
        and optionally fills missing values with safe type-based medians.
        """
        if isinstance(submission_input, (str, Path)):
            parsed_dict, _, _ = self.load_submission_csv(submission_input)
        else:
            parsed_dict = dict(submission_input)

        cleaned = {}
        repairs_applied = []

        # Calculate shape/type defaults for missing values
        type_defaults = {
            "money": 100_000_000.0,
            "percent": 50.0,
            "count": 2,
            "days": 730,
            "unknown": 0.0,
        }

        for qid in self.qids_expected:
            q_info = self.questions_data.get(qid, {})
            ans_type = q_info.get("answer_type", "unknown")

            if qid not in parsed_dict or parsed_dict[qid] is None:
                if fill_missing:
                    def_val = type_defaults.get(ans_type, 0.0)
                    cleaned[qid] = def_val
                    repairs_applied.append(f"Filled missing QID '{qid}' ({ans_type}) with default value {def_val}.")
                continue

            raw_val = parsed_dict[qid]
            is_num, num_val = is_valid_number(raw_val)

            if not is_num:
                if fill_missing:
                    def_val = type_defaults.get(ans_type, 0.0)
                    cleaned[qid] = def_val
                    repairs_applied.append(f"Replaced invalid value '{raw_val}' for QID '{qid}' with default {def_val}.")
                continue

            # Auto-rescale percentage if needed
            if ans_type == "percent":
                if auto_rescale_percent and check_percent_rescale_needed(num_val):
                    scaled = round(num_val * 100.0, 2)
                    repairs_applied.append(f"Rescaled fractional percentage {num_val} -> {scaled}% for QID '{qid}'.")
                    num_val = scaled
                elif num_val > 100.0 or num_val < 0.0:
                    def_val = 50.0
                    repairs_applied.append(f"Out-of-bounds percentage {num_val} for QID '{qid}' reset to default {def_val}%.")
                    num_val = def_val
                else:
                    num_val = round(num_val, 2)
            elif ans_type == "days":
                if num_val > 18250 or num_val < 0:
                    def_val = 730
                    repairs_applied.append(f"Out-of-bounds days {num_val} for QID '{qid}' reset to default {def_val}.")
                    num_val = def_val
                else:
                    num_val = round(num_val)
            elif ans_type == "count":
                if num_val > 10000 or num_val < 0:
                    def_val = 2
                    repairs_applied.append(f"Out-of-bounds count {num_val} for QID '{qid}' reset to default {def_val}.")
                    num_val = def_val
                else:
                    num_val = round(num_val)
            elif ans_type == "money":
                if num_val < 0:
                    def_val = 100_000_000.0
                    repairs_applied.append(f"Negative money {num_val} for QID '{qid}' reset to default {def_val}.")
                    num_val = def_val
                else:
                    num_val = round(num_val, 2)

            cleaned[qid] = num_val

        # Write to output CSV if requested
        if output_csv_path:
            out_path = Path(output_csv_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["question_id", "answer"])
                for qid in sorted(cleaned.keys()):
                    val = cleaned[qid]
                    # Format nicely: integer without .0 if integer
                    val_str = str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                    writer.writerow([qid, val_str])

        return cleaned, repairs_applied
