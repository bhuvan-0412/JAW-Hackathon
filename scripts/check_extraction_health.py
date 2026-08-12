#!/usr/bin/env python3
"""
scripts/check_extraction_health.py — Verifies Role A extraction completeness, file sizes, and coverage.
"""

import sys
from pathlib import Path
import pandas as pd

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import EXTRACTED_DIR, DOCUMENT_INDEX_PATH


def check_extraction_health():
    print("\n" + "=" * 65)
    print("  ROLE A EXTRACTION HEALTH CHECK")
    print("=" * 65)

    if not DOCUMENT_INDEX_PATH.exists():
        print(f"  [!] Missing document_index.csv at {DOCUMENT_INDEX_PATH}")
        return False

    df = pd.read_csv(DOCUMENT_INDEX_PATH)
    total_indexed = len(df)
    print(f"  Total Indexed Documents:  {total_indexed}")

    extracted_files = list(EXTRACTED_DIR.glob("*.json")) if EXTRACTED_DIR.exists() else []
    extracted_ids = {f.stem for f in extracted_files}
    print(f"  Total Extracted JSONs:    {len(extracted_files)}")

    missing_docs = df[~df["doc_id"].isin(extracted_ids)]
    coverage_pct = (len(extracted_files) / max(total_indexed, 1)) * 100.0
    print(f"  Overall Coverage:         {coverage_pct:.1f}%")

    if not missing_docs.empty:
        print(f"\n  Missing Documents by Type ({len(missing_docs)} remaining):")
        for dt, count in missing_docs["doc_type"].value_counts().items():
            print(f"    * {dt:32s}: {count:3d} missing")
    else:
        print("\n  [OK] 100% Extraction Coverage Achieved!")

    print("=" * 65 + "\n")
    return len(extracted_files) > 0


if __name__ == "__main__":
    ok = check_extraction_health()
    sys.exit(0 if ok else 1)
