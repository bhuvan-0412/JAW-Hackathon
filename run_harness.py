#!/usr/bin/env python3
"""
run_harness.py — Master CLI for Role D Evaluation, Validation & Integration Harness.

Modes:
    1. e2e               — Run full pipeline: Extraction check -> Entity Store -> Solver -> Validation -> Benchmark -> Export.
    2. validate          — Validate and audit submission CSV.
    3. benchmark         — Score submission against sample/hidden questions with deep diagnostics.
    4. compare           — Compare two submissions to track regressions and improvements.
    5. generate-baseline — Generate a validated baseline submission from current extracted data.
    6. self-test         — Run test suites and scorer mathematical verification.

Examples:
    python run_harness.py --mode e2e --out submissions/my_final_submission.csv
    python run_harness.py --mode validate --submission sample_submission.csv
    python run_harness.py --mode benchmark --submission sample_submission.csv --questions sample_questions.json
    python run_harness.py --mode compare --baseline sub1.csv --candidate sub2.csv
    python run_harness.py --mode self-test
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import (
    QUESTIONS_PATH,
    SAMPLE_QUESTIONS_PATH,
    SAMPLE_SUBMISSION_PATH,
    OUTPUTS_DIR,
    REPORTS_DIR,
)
from src.integration.orchestrator import PipelineOrchestrator
from src.validation.validator import SubmissionValidator
from src.evaluation.benchmark import HarnessEvaluator
from src.evaluation.comparator import SubmissionComparator
from src.reporting.reporter import ReportGenerator
from score_submission import run_self_test


def main():
    parser = argparse.ArgumentParser(
        description="Role D Master Harness — Bid Intelligence over a Document Estate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--mode",
        choices=["e2e", "validate", "benchmark", "compare", "generate-baseline", "self-test"],
        default="e2e",
        help="Operation mode"
    )
    parser.add_argument("--submission", help="Path to submission CSV")
    parser.add_argument("--questions", help="Path to questions JSON")
    parser.add_argument("--baseline", help="Baseline CSV for comparison mode")
    parser.add_argument("--candidate", help="Candidate CSV for comparison mode")
    parser.add_argument("--out", default="final_submission.csv", help="Output filename for generated submission")
    parser.add_argument("--report", help="Output path for Markdown report")
    parser.add_argument("--no-cache", action="store_true", help="Disable answer caching in e2e mode")
    args = parser.parse_args()

    orchestrator = PipelineOrchestrator()

    if args.mode == "self-test":
        print("\n[*] Running Role D Scorer Self-Test...")
        ok = run_self_test()
        sys.exit(0 if ok else 1)

    elif args.mode in ("e2e", "generate-baseline"):
        q_path = args.questions or QUESTIONS_PATH
        out_csv, val_res, bench_rep = orchestrator.run_full_pipeline(
            questions_path=q_path,
            submission_filename=args.out,
            use_cache=not args.no_cache,
            verbose=True
        )
        sys.exit(0 if val_res.is_valid else 1)

    elif args.mode == "validate":
        sub_path = args.submission or SAMPLE_SUBMISSION_PATH
        q_path = args.questions or QUESTIONS_PATH
        validator = SubmissionValidator(questions_path=q_path)
        res = validator.validate(sub_path)
        print(ReportGenerator.format_validation_terminal(res))
        if args.report:
            ReportGenerator.generate_validation_markdown(res, args.report)
            print(f"[*] Validation report saved to: {args.report}")
        sys.exit(0 if res.is_valid else 1)

    elif args.mode == "benchmark":
        sub_path = args.submission or SAMPLE_SUBMISSION_PATH
        q_path = args.questions or SAMPLE_QUESTIONS_PATH
        validator = SubmissionValidator(questions_path=q_path)
        parsed, _, _ = validator.load_submission_csv(sub_path)
        evaluator = HarnessEvaluator(questions_path=q_path)
        rep = evaluator.evaluate(parsed)
        print(ReportGenerator.format_benchmark_terminal(rep))
        if args.report:
            ReportGenerator.generate_benchmark_markdown(rep, args.report)
            print(f"[*] Benchmark report saved to: {args.report}")
        sys.exit(0)

    elif args.mode == "compare":
        if not args.baseline or not args.candidate:
            parser.error("--baseline and --candidate are required in compare mode.")
        validator = SubmissionValidator()
        b_dict, _, _ = validator.load_submission_csv(args.baseline)
        c_dict, _, _ = validator.load_submission_csv(args.candidate)
        diff_rep = SubmissionComparator.compare(b_dict, c_dict)
        print("\n" + "=" * 65)
        print(f"  COMPARISON: {args.baseline} vs {args.candidate}")
        print(f"  Identical: {diff_rep.identical_count} | Changed: {diff_rep.changed_count}")
        print("=" * 65 + "\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
