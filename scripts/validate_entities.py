#!/usr/bin/env python3
"""
scripts/validate_entities.py — Audits extracted/*.json documents against entities_schema.md requirements.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import EXTRACTED_DIR


REQUIRED_FIELDS_BY_TYPE = {
    "completion_certificate": ["project_name", "client_name", "contract_value"],
    "company_completion_certificate": ["project_name", "client_name", "contract_value"],
    "reference_letter": ["project_name", "issuing_client"],
    "performance_bond": ["project_name", "guarantee_amount"],
    "personnel_certificate": ["engineer_name", "certification_type"],
    "cv": ["engineer_name"],
    "ra_bill": ["project_name", "contract_value"],
    "final_ra_bill": ["project_name", "contract_value"],
}


def validate_extracted_entities():
    print("\n" + "=" * 65)
    print("  EXTRACTED ENTITIES SCHEMA AUDIT")
    print("=" * 65)

    if not EXTRACTED_DIR.exists():
        print(f"  [!] Extracted directory {EXTRACTED_DIR} does not exist.")
        return False

    json_files = list(EXTRACTED_DIR.glob("*.json"))
    print(f"  Total Extracted JSONs:    {len(json_files)}")

    if not json_files:
        print("  [!] No JSON files found in extracted/.")
        return False

    by_type = {}
    missing_fields_count = 0
    parse_errors = 0

    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            parse_errors += 1
            continue

        doc_type = data.get("doc_type", "unknown")
        ext = data.get("extracted_data") or {}

        if doc_type not in by_type:
            by_type[doc_type] = {"total": 0, "has_extracted_data": 0, "missing_core": 0}

        by_type[doc_type]["total"] += 1
        if ext:
            by_type[doc_type]["has_extracted_data"] += 1

        req_fields = REQUIRED_FIELDS_BY_TYPE.get(doc_type, [])
        for f in req_fields:
            if ext.get(f) is None:
                by_type[doc_type]["missing_core"] += 1
                missing_fields_count += 1
                break

    print("\n  Extraction Coverage by Document Type:")
    print(f"  {'Doc Type':32s} {'Total':>6s} {'Has Data':>10s} {'Missing Key Fields':>20s}")
    print("  " + "-" * 70)
    for dt, stats in sorted(by_type.items()):
        print(f"  {dt:32s} {stats['total']:6d} {stats['has_extracted_data']:10d} {stats['missing_core']:20d}")

    print(f"\n  Total Parse Errors:       {parse_errors}")
    print("=" * 65 + "\n")
    return parse_errors == 0


if __name__ == "__main__":
    ok = validate_extracted_entities()
    sys.exit(0 if ok else 1)
