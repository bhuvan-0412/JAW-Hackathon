"""
src/integration/orchestrator.py — Master pipeline coordinator integrating Role A, B, C, and D.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple

from src.config import (
    QUESTIONS_PATH,
    SAMPLE_QUESTIONS_PATH,
    CACHE_DIR,
    OUTPUTS_DIR,
    REPORTS_DIR,
)
from src.validation.validator import SubmissionValidator, ValidationResult
from src.evaluation.benchmark import HarnessEvaluator, BenchmarkReport
from src.reporting.reporter import ReportGenerator
from .adapters import (
    RoleAAdapter,
    RoleBAdapter,
    RoleCAdapter,
    DefaultRoleAAdapter,
    DefaultRoleBAdapter,
    BaselineRoleCAdapter,
)


class PipelineOrchestrator:
    """
    Master integration coordinator. Orchestrates extraction checks, entity store queries,
    question solving, answer caching, validation audits, benchmark scoring, and submission generation.
    """

    def __init__(
        self,
        role_a: Optional[RoleAAdapter] = None,
        role_b: Optional[RoleBAdapter] = None,
        role_c: Optional[RoleCAdapter] = None,
        cache_dir: Union[str, Path] = CACHE_DIR,
        outputs_dir: Union[str, Path] = OUTPUTS_DIR,
        reports_dir: Union[str, Path] = REPORTS_DIR,
    ):
        self.role_a = role_a or DefaultRoleAAdapter()
        self.role_b = role_b or DefaultRoleBAdapter()
        self.role_c = role_c or BaselineRoleCAdapter()
        self.cache_dir = Path(cache_dir)
        self.outputs_dir = Path(outputs_dir)
        self.reports_dir = Path(reports_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.validator = SubmissionValidator()
        self.evaluator = HarnessEvaluator()

    def run_full_pipeline(
        self,
        questions_path: Union[str, Path] = QUESTIONS_PATH,
        submission_filename: str = "final_submission.csv",
        use_cache: bool = True,
        verbose: bool = True
    ) -> Tuple[Path, ValidationResult, Optional[BenchmarkReport]]:
        """
        Executes end-to-end integration and produces verified submission.csv + reports.
        """
        t0 = time.time()
        q_path = Path(questions_path)

        if verbose:
            print("\n" + "=" * 65)
            print("  STARTING INTEGRATION PIPELINE RUN")
            print("=" * 65)

        # 1. Check Role A Extraction Status
        a_stats = self.role_a.get_coverage_stats()
        if verbose:
            print(f"[*] Role A Status: {a_stats['extracted_count']}/{a_stats['total_indexed']} documents extracted ({a_stats['coverage_pct']:.1f}% coverage)")

        # 2. Load Questions
        with open(q_path, "r", encoding="utf-8") as f:
            q_data = json.load(f)
        questions_list = q_data.get("questions") or q_data.get("answers") or []
        total_q = len(questions_list)

        if verbose:
            print(f"[*] Loaded {total_q} questions from {q_path.name}")

        # 3. Answer Generation with Caching
        cache_file = self.cache_dir / f"answers_cache_{q_path.stem}.json"
        answers_cache = {}
        if use_cache and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    answers_cache = json.load(f)
                if verbose:
                    print(f"[*] Loaded {len(answers_cache)} cached answers from {cache_file.name}")
            except Exception:
                answers_cache = {}

        raw_answers = dict(answers_cache)
        solved_now = 0

        for idx, q in enumerate(questions_list, start=1):
            qid = q.get("qid")
            if not qid:
                continue

            if qid in raw_answers and raw_answers[qid] is not None:
                continue

            ans = self.role_c.solve(q)
            raw_answers[qid] = ans
            solved_now += 1

            if verbose and (idx % 50 == 0 or idx == total_q):
                print(f"    - Solved [{idx}/{total_q}] questions...")

        # Save cache
        if solved_now > 0 or not cache_file.exists():
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(raw_answers, f, indent=2)

        if verbose:
            print(f"[*] Solved {solved_now} new questions (total answered: {len(raw_answers)}/{total_q})")

        # 4. Validation & Sanitization (Role D)
        validator = SubmissionValidator(questions_path=q_path)
        out_p = Path(submission_filename)
        if out_p.is_absolute():
            out_csv_path = out_p
        elif str(out_p).startswith("submissions") or str(out_p).startswith("submissions/"):
            out_csv_path = self.outputs_dir.parent / out_p
        else:
            out_csv_path = self.outputs_dir / out_p
        out_csv_path.parent.mkdir(parents=True, exist_ok=True)
        cleaned_answers, repairs = validator.sanitize_and_repair(
            raw_answers,
            output_csv_path=out_csv_path,
            auto_rescale_percent=True,
            fill_missing=True
        )

        val_result = validator.validate(out_csv_path)

        if verbose:
            print(ReportGenerator.format_validation_terminal(val_result))

        # Generate validation markdown report
        val_report_path = self.reports_dir / "VALIDATION_REPORT.md"
        ReportGenerator.generate_validation_markdown(val_result, val_report_path)

        # 5. Benchmark Calibration (on sample questions if available)
        bench_report = None
        if SAMPLE_QUESTIONS_PATH.exists():
            # Solve sample questions for calibration
            sample_answers = {}
            with open(SAMPLE_QUESTIONS_PATH, "r", encoding="utf-8") as f:
                sq_data = json.load(f)
            sq_list = sq_data.get("questions") or []

            for sq in sq_list:
                sample_answers[sq["qid"]] = self.role_c.solve(sq)

            sample_evaluator = HarnessEvaluator(SAMPLE_QUESTIONS_PATH)
            bench_report = sample_evaluator.evaluate(sample_answers)

            if verbose:
                print(ReportGenerator.format_benchmark_terminal(bench_report))

            bench_report_path = self.reports_dir / "EVALUATION_REPORT.md"
            ReportGenerator.generate_benchmark_markdown(bench_report, bench_report_path)

        elapsed = time.time() - t0
        if verbose:
            print(f"[*] Pipeline completed successfully in {elapsed:.2f}s!")
            print(f"[*] Output CSV: {out_csv_path}")
            print(f"[*] Validation Report: {val_report_path}")
            if bench_report:
                print(f"[*] Evaluation Benchmark Report: {self.reports_dir / 'EVALUATION_REPORT.md'}")
            print("=" * 65 + "\n")

        return out_csv_path, val_result, bench_report
