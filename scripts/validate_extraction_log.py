#!/usr/bin/env python3
"""
scripts/validate_extraction_log.py — Audits extraction_log.jsonl for extraction status, errors, and formatting.
"""

import sys
import json
from pathlib import Path
import pandas as pd

# Add repo root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import DOCUMENT_INDEX_PATH, WORKSPACE_DIR

LOG_PATH = WORKSPACE_DIR / "extraction_log.jsonl"


def validate_extraction_log():
    print("\n" + "=" * 65)
    print("  EXTRACTION LOG AUDIT")
    print("=" * 65)

    if not LOG_PATH.exists():
        print(f"  [!] Warning: {LOG_PATH.name} does not exist.")
        return False

    records = []
    line_errors = 0
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                line_errors += 1

    total_entries = len(records)
    print(f"  Total Log Records:        {total_entries}")
    print(f"  JSON Decode Errors:       {line_errors}")

    if total_entries == 0:
        print("  [!] No valid log entries found.")
        return False

    # Status distribution
    status_counts = {}
    error_entries = []
    for r in records:
        st = r.get("status", "UNKNOWN")
        status_counts[st] = status_counts.get(st, 0) + 1
        if st in ("ERROR", "FAILED") or r.get("error"):
            error_entries.append(r)

    print("\n  Status Distribution:")
    for st, count in sorted(status_counts.items()):
        print(f"    * {st:15s}: {count:4d} ({count/total_entries:.1%})")

    # Cross-check with document_index.csv
    if DOCUMENT_INDEX_PATH.exists():
        df = pd.read_csv(DOCUMENT_INDEX_PATH)
        indexed_ids = set(df["doc_id"].dropna().tolist())
        logged_ids = set(r.get("doc_id") for r in records if r.get("doc_id"))
        missing_from_log = indexed_ids - logged_ids
        print(f"\n  Document Index Parity:")
        print(f"    * Total Indexed Docs:   {len(indexed_ids)}")
        print(f"    * Logged Docs in File:  {len(logged_ids)}")
        print(f"    * Unlogged Docs Count:  {len(missing_from_log)}")
        if missing_from_log:
            sample_unlogged = sorted(list(missing_from_log))[:5]
            print(f"    * Sample Unlogged:      {sample_unlogged}...")

    print("=" * 65 + "\n")
    return line_errors == 0


if __name__ == "__main__":
    ok = validate_extraction_log()
    sys.exit(0 if ok else 1)
