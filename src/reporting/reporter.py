"""
src/reporting/reporter.py — Generates markdown reports and formatted terminal dashboards.
"""

from typing import Dict, List, Optional, Union, Any
from pathlib import Path
import datetime

from src.validation.validator import ValidationResult, IssueSeverity
from src.evaluation.benchmark import BenchmarkReport
from src.evaluation.comparator import DiffReport


class ReportGenerator:
    """
    Produces formatted Markdown and terminal reports for Role D outputs.
    """

    @staticmethod
    def format_validation_terminal(res: ValidationResult) -> str:
        lines = []
        status = "[PASSED]" if res.is_valid else "[FAILED]"
        lines.append("\n" + "=" * 65)
        lines.append(f"  SUBMISSION VALIDATION SUMMARY -- {status}")
        lines.append("=" * 65)
        lines.append(f"  Total Questions Expected:  {res.total_questions_expected}")
        lines.append(f"  Total Questions Found:     {res.total_questions_found}")
        lines.append(f"  Valid Answers Count:       {res.valid_answers_count}")
        lines.append(f"  Pass Rate:                 {res.pass_rate:.1f}%")
        lines.append(f"  Errors:                    {res.error_count}")
        lines.append(f"  Warnings:                  {res.warning_count}")

        if res.missing_qids:
            lines.append(f"\n  [!] Missing QIDs ({len(res.missing_qids)}): {res.missing_qids[:5]}...")

        if res.anomalies:
            lines.append("\n  Detected Anomalies:")
            for a in res.anomalies:
                lines.append(f"    * {a}")

        lines.append("=" * 65 + "\n")
        return "\n".join(lines)

    @staticmethod
    def generate_validation_markdown(res: ValidationResult, output_path: Union[str, Path]) -> None:
        lines = [
            "# Submission Validation Report",
            "",
            f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"**Status:** {'**PASSED** (Ready for submission)' if res.is_valid else '**FAILED** (Issues must be resolved)'}",
            "",
            "## Summary Metrics",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Total Questions Expected | `{res.total_questions_expected}` |",
            f"| Total Questions Found | `{res.total_questions_found}` |",
            f"| Valid Answers Count | `{res.valid_answers_count}` |",
            f"| Validation Pass Rate | `{res.pass_rate:.1f}%` |",
            f"| Critical Errors | `{res.error_count}` |",
            f"| Warnings | `{res.warning_count}` |",
            "",
            "## Breakdown by Answer Type",
            "",
            "| Type | Total | Valid | Zeros | Total Sum |",
            "|---|---:|---:|---:|---:|",
        ]

        for t_name, data in res.type_breakdown.items():
            lines.append(f"| `{t_name}` | {data['total']} | {data['valid']} | {data['zeros']} | {data['sum']:,.2f} |")

        if res.anomalies:
            lines.extend([
                "",
                "## Statistical Anomalies Detected",
                "",
            ])
            for a in res.anomalies:
                lines.append(f"- {a}")

        if res.issues:
            lines.extend([
                "",
                "## Issue Log (Top 25)",
                "",
                "| Severity | QID | Code | Message | Raw Value |",
                "|---|---|---|---|---|",
            ])
            for iss in res.issues[:25]:
                sev_badge = "ERROR" if iss.severity == IssueSeverity.ERROR else "WARN"
                raw_v = f"`{iss.raw_value}`" if iss.raw_value is not None else "-"
                lines.append(f"| {sev_badge} | `{iss.qid}` | `{iss.code}` | {iss.message} | {raw_v} |")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @staticmethod
    def format_benchmark_terminal(rep: BenchmarkReport) -> str:
        lines = []
        lines.append("\n" + "=" * 65)
        lines.append(f"  BENCHMARK SCORE: {rep.total_score:.2f} / {rep.max_score:.0f} ({rep.overall_percentage:.1f}%)")
        lines.append("=" * 65)

        lines.append(f"  Answered: {rep.answered_questions}/{rep.total_questions}\n")

        lines.append(f"  {'Shape':26s} {'Score':>8s}  {'N':>3s}  {'Acc %':>7s}")
        lines.append("  " + "-" * 50)
        for k, cat in rep.by_shape.items():
            lines.append(f"  {k:26s} {cat.score:8.2f}  {cat.count:3d}   {cat.percentage:6.1f}%")

        lines.append("\n  Error Distribution:")
        for bucket, count in rep.error_histogram.items():
            pct = (count / max(rep.total_questions, 1)) * 100.0
            lines.append(f"    * {bucket:18s}: {count:3d} ({pct:5.1f}%)")

        lines.append("=" * 65 + "\n")
        return "\n".join(lines)

    @staticmethod
    def generate_benchmark_markdown(rep: BenchmarkReport, output_path: Union[str, Path]) -> None:
        lines = [
            "# Evaluation Benchmark Report",
            "",
            f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"## Overall Score: `{rep.total_score:.2f} / {rep.max_score:.0f}` (`{rep.overall_percentage:.2f}%`)",
            "",
            f"- **Answered Questions:** `{rep.answered_questions} / {rep.total_questions}`",
            "",
            "## Score Breakdown by Question Shape",
            "",
            "| Shape | Score | Count | Accuracy |",
            "|---|---:|---:|---:|",
        ]

        for k, cat in rep.by_shape.items():
            lines.append(f"| `{k}` | {cat.score:.2f} | {cat.count} | **{cat.percentage:.1f}%** |")

        lines.extend([
            "",
            "## Score Breakdown by Answer Type",
            "",
            "| Answer Type | Score | Count | Accuracy |",
            "|---|---:|---:|---:|",
        ])
        for k, cat in rep.by_type.items():
            lines.append(f"| `{k}` | {cat.score:.2f} | {cat.count} | **{cat.percentage:.1f}%** |")

        lines.extend([
            "",
            "## Error Histogram",
            "",
            "| Closeness Tier | Questions | Share |",
            "|---|---:|---:|",
        ])
        for bucket, count in rep.error_histogram.items():
            pct = (count / max(rep.total_questions, 1)) * 100.0
            lines.append(f"| `{bucket}` | {count} | {pct:.1f}% |")

        if rep.worst_misses:
            lines.extend([
                "",
                "## High Priority Diagnostic Misses (Worst Performing)",
                "",
                "| QID | Shape | Gold | Got | Score | Error % |",
                "|---|---|---:|---:|---:|---:|",
            ])
            for m in rep.worst_misses:
                got_str = f"{m.got:,.2f}" if m.got is not None else "None"
                lines.append(f"| `{m.qid}` | `{m.shape}` | {m.gold:,.2f} | {got_str} | {m.score:.3f} | {m.error_pct:.1f}% |")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
