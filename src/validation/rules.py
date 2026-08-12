"""
src/validation/rules.py — Core validation rules and constraints for hackathon submissions.
"""

import math
from typing import Optional, Tuple, Any
from src.config import VALIDATION_BOUNDS, COMPANY_METADATA


def is_valid_number(val: Any) -> Tuple[bool, Optional[float]]:
    """
    Check if a value is a valid, finite real number.
    Returns (is_valid, float_val).
    """
    if val is None:
        return False, None
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return False, None
        return True, float(val)
    if isinstance(val, str):
        cleaned = val.strip().replace(",", "").replace("₹", "").replace("INR", "").replace("%", "").strip()
        try:
            f = float(cleaned)
            if math.isnan(f) or math.isinf(f):
                return False, None
            return True, f
        except ValueError:
            return False, None
    return False, None


def check_percent_rescale_needed(val: float) -> bool:
    """
    Detects if a percentage value was likely submitted as a [0.0, 1.0] fraction
    rather than a [0.0, 100.0] percentage.
    e.g. 0.3333 instead of 33.33.
    """
    if 0.0 < val <= 1.0:
        return True
    return False


def validate_single_answer(qid: str, answer: Any, answer_type: str) -> list[dict]:
    """
    Validate a single QID's answer against type rules and bounds.
    Returns a list of issue dictionaries if invalid.
    """
    issues = []
    is_num, num_val = is_valid_number(answer)

    if not is_num:
        issues.append({
            "qid": qid,
            "severity": "ERROR",
            "code": "INVALID_NUMBER",
            "message": f"Answer '{answer}' is not a valid finite number or is missing."
        })
        return issues

    # Type-specific rules
    bounds = VALIDATION_BOUNDS.get(answer_type, {})

    if answer_type == "percent":
        min_v = bounds.get("min", 0.0)
        max_v = bounds.get("max", 100.0)
        if num_val < min_v or num_val > max_v:
            issues.append({
                "qid": qid,
                "severity": "ERROR",
                "code": "OUT_OF_BOUNDS_PERCENT",
                "message": f"Percentage {num_val} is outside valid range [{min_v}, {max_v}]."
            })
        elif check_percent_rescale_needed(num_val):
            issues.append({
                "qid": qid,
                "severity": "WARNING",
                "code": "FRACTION_PERCENT_SUSPECTED",
                "message": f"Percentage {num_val} is in (0, 1]. Did you mean {num_val * 100.0:.2f}%?"
            })

    elif answer_type == "days":
        min_v = bounds.get("min", 0)
        max_v = bounds.get("max", 365 * 50)
        if num_val < min_v:
            issues.append({
                "qid": qid,
                "severity": "ERROR",
                "code": "NEGATIVE_DAYS",
                "message": f"Days elapsed cannot be negative ({num_val})."
            })
        elif num_val > max_v:
            issues.append({
                "qid": qid,
                "severity": "WARNING",
                "code": "SUSPICIOUS_DAYS",
                "message": f"Days value {num_val} exceeds realistic project lifespan (> 50 years)."
            })

    elif answer_type == "count":
        min_v = bounds.get("min", 0)
        max_v = bounds.get("max", 10_000)
        if num_val < min_v:
            issues.append({
                "qid": qid,
                "severity": "ERROR",
                "code": "NEGATIVE_COUNT",
                "message": f"Count cannot be negative ({num_val})."
            })
        elif not num_val.is_integer():
            issues.append({
                "qid": qid,
                "severity": "WARNING",
                "code": "NON_INTEGER_COUNT",
                "message": f"Count {num_val} is not an integer."
            })

    elif answer_type == "money":
        min_v = bounds.get("min", -100_000_000_000.0)
        max_v = bounds.get("max", 100_000_000_000.0)
        if num_val < 0.0:
            issues.append({
                "qid": qid,
                "severity": "WARNING",
                "code": "NEGATIVE_MONEY",
                "message": f"Money value is negative ({num_val}). Verify question explicitly asks for signed difference."
            })
        elif num_val > COMPANY_METADATA["total_delivered_value_inr"] * 2:
            issues.append({
                "qid": qid,
                "severity": "WARNING",
                "code": "SUSPICIOUS_HIGH_MONEY",
                "message": f"Money value {num_val:,.0f} exceeds 2x total company historical revenue ({COMPANY_METADATA['total_delivered_value_inr']:,.0f})."
            })

    return issues
