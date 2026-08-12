#!/usr/bin/env python3
"""
scripts/full_pipeline_check.py — Comprehensive end-to-end smoke test for the entire hackathon system.
Verifies Role A, Role B, Role C, and Role D components and ensures submission readiness.
"""

import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import (
    QUESTIONS_PATH,
    SAMPLE_QUESTIONS_PATH,
    OUTPUTS_DIR,
    REPORTS_DIR,
    DOCUMENT_INDEX_PATH,
)
from src.integration.orchestrator import PipelineOrchestrator
from score_submission import run_self_test
from scripts.check_extraction_health import check_extraction_health
from scripts.check_graph_health import check_graph_health


def main():
    t0 = time.time()
    print("\n" + "#" * 65)
    print("  RUNNING FULL PIPELINE & HARNESS SMOKE TEST")
    print("#" * 65)

    checks = []

    # 1. Scorer Self-Test
    print("\n[Step 1/5] Verifying Scorer Math and Official Formula...")
    scorer_ok = run_self_test()
    checks.append(("Scorer Math Verification", scorer_ok))

    # 2. Role A Extraction Health
    print("\n[Step 2/5] Checking Role A Document Extraction Health...")
    ext_ok = check_extraction_health()
    checks.append(("Role A Extraction Health", ext_ok))

    # 3. Role B Entity Graph
    print("\n[Step 3/5] Checking Role B Entity Database & Linkages...")
    graph_ok = check_graph_health()
    checks.append(("Role B Graph Health", graph_ok))

    # 4. End-to-End Pipeline Execution (Role C + Role D)
    print("\n[Step 4/5] Executing End-to-End Pipeline on Competition Questions...")
    orchestrator = PipelineOrchestrator()
    out_csv, val_res, bench_rep = orchestrator.run_full_pipeline(
        questions_path=QUESTIONS_PATH,
        submission_filename="final_submission.csv",
        use_cache=True,
        verbose=False
    )
    pipeline_ok = val_res.is_valid and out_csv.exists()
    checks.append(("E2E Submission Generation", pipeline_ok))
    checks.append(("Submission Validation (333 rows)", val_res.is_valid))

    # 5. Benchmark Calibration
    print("\n[Step 5/5] Checking Benchmark Reports...")
    bench_ok = (REPORTS_DIR / "EVALUATION_REPORT.md").exists() and (REPORTS_DIR / "VALIDATION_REPORT.md").exists()
    checks.append(("Reports Generation", bench_ok))

    # Summary
    elapsed = time.time() - t0
    print("\n" + "=" * 65)
    print("  PIPELINE SMOKE TEST SUMMARY")
    print("=" * 65)
    all_passed = True
    for name, ok in checks:
        badge = "[PASS]" if ok else "[FAIL]"
        if not ok:
            all_passed = False
        print(f"  {name:35s}: {badge}")

    print(f"\n  Total Execution Time: {elapsed:.2f}s")
    status_text = "ALL CHECKS PASSED -- READY FOR SUBMISSION" if all_passed else "SOME CHECKS FAILED"
    print(f"  Final Status:         {status_text}")
    print("=" * 65 + "\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
