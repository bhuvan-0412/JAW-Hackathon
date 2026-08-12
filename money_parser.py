#!/usr/bin/env python3
"""
money_parser.py — Standardized parser for monetary figures in Indian currency formats.

Handles:
  - INR / Rs / ₹ prefixes, /- suffixes
  - Crore / Cr / Crores multiplier (10,000,000)
  - Lakh / Lakhs / Lac / Lacs multiplier (100,000)
  - Thousand / K multiplier (1,000)
  - Indian digit grouping (e.g. 33,38,00,000) & standard numbers
"""

import re
from typing import Any, List, Tuple, Optional

# Regular expression patterns for money parsing
_MONEY_REGEX = re.compile(
    r'(?:INR|Rs\.?|₹)?\s*'
    r'([\d,]+(?:\.\d+)?)\s*'
    r'(Crores?|Cr|Lakhs?|Lacs?|Lakh|Lac|Thousand|K)?'
    r'(?:\s*/-)?',
    re.IGNORECASE
)

_MENTION_REGEX = re.compile(
    r'(?:INR|Rs\.?|₹)\s*[\d,]+(?:\.\d+)?(?:\s*(?:Crores?|Cr|Lakhs?|Lacs?|Lakh|Lac|Thousand|K))?(?:\s*/-)?'
    r'|[\d,]+(?:\.\d+)?\s*(?:Crores?|Cr|Lakhs?|Lacs?|Lakh|Lac)\b',
    re.IGNORECASE
)


def parse_money(text: str) -> Optional[float]:
    """
    Parse a single monetary text string into a float representing Rupees.
    Returns None if text cannot be parsed as a valid money figure.
    """
    if text is None:
        return None
    
    if isinstance(text, (int, float)):
        return float(text)
        
    s = str(text).strip()
    if not s:
        return None

    try:
        # Clean up trailing /- or currency symbols
        cleaned = re.sub(r'/(?:-)?$', '', s).strip()
        cleaned = re.sub(r'^(?:INR|Rs\.?|₹)\s*', '', cleaned, flags=re.IGNORECASE).strip()

        # Match number + unit
        match = re.match(r'^([\d,]+(?:\.\d+)?)\s*(Crores?|Cr|Lakhs?|Lacs?|Lakh|Lac|Thousand|K)?$', cleaned, re.IGNORECASE)
        if not match:
            # Fallback: try removing commas and extracting numeric value
            num_part = cleaned.replace(',', '')
            if not num_part:
                return None
            return float(num_part)

        val_str, unit = match.groups()
        if not val_str or not val_str.replace(',', '').strip():
            return None
            
        num_val = float(val_str.replace(',', ''))

        if unit:
            u = unit.lower()
            if u in ('cr', 'crore', 'crores'):
                num_val *= 10_000_000.0
            elif u in ('lakh', 'lakhs', 'lac', 'lacs'):
                num_val *= 100_000.0
            elif u in ('thousand', 'k'):
                num_val *= 1_000.0

        return num_val
    except (ValueError, TypeError, AttributeError):
        return None


def find_money_mentions(text: str) -> List[Tuple[str, float]]:
    """
    Find all monetary mentions in a text string.
    Returns a list of tuples: (raw_mention_text, parsed_float_value).
    """
    if not text:
        return []
        
    results = []
    matches = _MENTION_REGEX.finditer(text)
    for m in matches:
        raw_str = m.group(0)
        parsed = parse_money(raw_str)
        if parsed is not None:
            results.append((raw_str, parsed))
    return results


def parse_cell_value(val: Any) -> Optional[float]:
    """
    Parse a cell value from Excel or tabular data.
    Safely converts integers, floats, and monetary strings into float values in Rupees.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    return parse_money(str(val))


if __name__ == '__main__':
    test_cases = [
        ("INR 33.38 Cr", 333800000.0),
        ("3,338.00 Lakh", 333800000.0),
        ("33,38,00,000", 333800000.0),
        ("333800000", 333800000.0),
        ("INR 13.40 Cr", 134000000.0),
        ("Rs. 81.44 Cr", 814400000.0),
        ("100/-", 100.0),
        ("INR 50,00,000/-", 5000000.0)
    ]
    all_passed = True
    for text, expected in test_cases:
        got = parse_money(text)
        status = "OK" if got == expected else f"FAIL (got {got})"
        print(f"[{status}] '{text}' -> {got} (expected {expected})")
        if got != expected:
            all_passed = False
    if all_passed:
        print("\nAll money_parser unit tests passed successfully!")
