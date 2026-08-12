# BITS Hackathon — Bid Intelligence over a Document Estate

You are given the complete document archive of a construction company. **There is no database.**
Your task is to build a system that reads those documents and answers precise numerical questions
about the business.

---

## 🚀 Quick Start (5-Minute Onboarding)

Get up and running in under 5 minutes:

```bash
pip install -r requirements.txt
python scripts/run_sample_score.py
python scripts/full_pipeline_check.py
python run_harness.py --mode e2e --out submissions/final_submission.csv
```

### System Requirements
* **Python**: 3.10+ (tested on Python 3.10, 3.11, 3.12)
* **OS**: Linux, macOS, or Windows

---

## 📁 Repository Structure

```text
├── documents/                    # 687 raw unstructured documents (678 PDFs, 9 Excel workbooks)
├── extracted/                    # Per-document structured JSON extractions (Role A)
├── evaluation/                   # Evaluation metadata, pattern definitions & reports
│   ├── patterns.yaml             # Multi-hop question taxonomy and shape rules
│   └── reports/                  # Generated benchmark and validation reports
├── reports/                      # Auto-generated markdown reports
│   ├── VALIDATION_REPORT.md      # Submission integrity and type conformance report
│   └── EVALUATION_REPORT.md      # Diagnostic benchmark accuracy report
├── scripts/                      # Role D automation, validation, and health checks
│   ├── run_sample_score.py       # Scores solver against sample_questions.json
│   ├── full_pipeline_check.py    # Complete smoke test across all 4 roles
│   ├── validate_extraction_log.py# Audits extraction log integrity
│   ├── validate_entities.py      # Checks entity schema conformance
│   ├── validate_answers.py       # Validates submission CSV formatting & bounds
│   ├── check_extraction_health.py# Verifies Role A document coverage
│   ├── check_graph_health.py     # Audits Role B entity graph & database connectivity
│   ├── pattern_breakdown.py      # Analyzes question distributions and hop complexity
│   ├── export_submission_csv.py  # Exports validated, bounds-checked submission CSV
│   ├── freeze_submission.py      # Computes SHA256, Git commit, and archives release manifest
│   └── update_score_history.py   # Logs historical benchmark scores to JSON
├── src/                          # Core Role D modular package
│   ├── config.py                 # Central configuration loader
│   ├── validation/               # Schema checks, type bounds (money, percent, days, count), auto-repair
│   ├── evaluation/               # Exact evaluate.py scoring parity, diagnostics, differential comparator
│   ├── reference_engine/         # SQLite entity store & multi-hop baseline solver
│   ├── integration/              # Role A/B/C adapters and master pipeline orchestrator
│   └── reporting/                # Terminal dashboards and Markdown report generators
├── submissions/                  # Submission output directory
│   ├── final_submission.csv      # 100% verified 333-row submission
│   ├── final_submission.manifest.json # Release manifest (SHA256, commit, row count)
│   └── archive/                  # Timestamped frozen release archives
├── tests/                        # Automated unit tests
│   ├── test_validator.py         # Format, bounds, and auto-repair tests
│   ├── test_scorer.py            # Scoring formula & parity tests
│   ├── test_comparator.py        # Submission diffing tests
│   └── test_reference_engine.py  # SQLite store & baseline solver tests
├── document_index.csv            # Mapping of doc_id, doc_type, filename, size_bytes
├── questions.json                # 333 competition questions to answer
├── sample_questions.json         # 21 calibration questions with gold answers & reasoning
├── evaluate.py                   # Official evaluation scorer
├── harness_config.py             # Global harness constants and validation rules
├── run_harness.py                # Master CLI tool
├── validate_submission.py        # Standalone submission validator CLI
├── score_submission.py           # Standalone scoring CLI
├── compare_submissions.py        # Submissions differential comparison CLI
├── requirements.txt              # Core runtime dependencies
├── requirements-dev.txt          # Development and testing dependencies
└── PUSH_CHECKLIST.md             # Pre-push release verification checklist
```

---

## 🛠️ Role D Tooling & Commands

### 1. End-to-End Pipeline Execution
Runs the full pipeline (Role A Extraction -> Role B Entity Store -> Role C Solver -> Role D Validation & Benchmarking):
```bash
python run_harness.py --mode e2e --out submissions/final_submission.csv
```

### 2. Validate Submission Integrity
Strictly validates format, checks exact 333 question IDs, and enforces numeric bounds:
```bash
python validate_submission.py --submission submissions/final_submission.csv --report reports/VALIDATION_REPORT.md
```

### 3. Auto-Repair & Clean Submissions
Auto-fixes formatting errors, strips symbols, rescales fraction percentages, and fills missing rows:
```bash
python validate_submission.py --submission submissions/my_raw.csv --fix-out submissions/cleaned.csv
```

### 4. Benchmark Scoring & Diagnostics
Scores answers against `sample_questions.json` with multi-dimensional breakdowns:
```bash
python score_submission.py --submission submissions/sample_answers_submission.csv --questions sample_questions.json --per-question
```

### 5. Compare Two Submissions (Regression Tracking)
Compare two candidate submissions to identify improved ($+\Delta$) and regressed ($-\Delta$) questions:
```bash
python compare_submissions.py --baseline submissions/sub_v1.csv --candidate submissions/sub_v2.csv
```

### 6. Freeze & Archive Final Release
Generates SHA256 checksums, records Git commit, creates `.manifest.json`, and archives timestamped files:
```bash
python scripts/freeze_submission.py --submission submissions/final_submission.csv
```

---

## 👥 Recommended Daily Team Workflow

1. **Role A (Extraction)**: Runs `python run_flush_all.py` to extract new PDFs/workbooks into `extracted/`. Check progress with `python scripts/check_extraction_health.py`.
2. **Role B (Knowledge Graph / Database)**: Updates entity relations in `src/reference_engine/entity_store.py` (or custom graph module). Check connectivity with `python scripts/check_graph_health.py`.
3. **Role C (Reasoning & Solver)**: Improves question traversal logic in `src/reference_engine/baseline_solver.py` (or custom solver). Check sample score with `python scripts/run_sample_score.py`.
4. **Role D (Validation & Integration)**: Runs `python scripts/full_pipeline_check.py` and `python run_harness.py --mode e2e`. Verifies [VALIDATION_REPORT.md](file:///c:/Users/visha/Downloads/JAW-Hackathon-1/reports/VALIDATION_REPORT.md) and creates frozen release manifest.

---

## 🔧 Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | Virtual environment missing dependencies | Run `pip install -r requirements.txt` |
| `Validation Failed: OUT_OF_BOUNDS_PERCENT` | Percentage submitted as fraction $[0, 1]$ or $>100$ | Run `python validate_submission.py --fix-out cleaned.csv` to auto-scale |
| `Scorer mismatch vs evaluate.py` | Trailing spaces or NaN values | Ensure all answers are cleaned numbers |
| `Upstream data missing` | Role A/B artifacts not yet extracted | Baseline solver automatically provides graceful heuristic fallbacks |

---

## 🏢 The Company & The Dataset

**National Infrastructure Corp. Ltd.** — an Indian infrastructure contractor, founded 2005, head office in Salt Lake, Kolkata.

| Metric | Value |
|---|---|
| Completed works | 155, delivered 2010 – 2025 |
| Clients | 62 government departments and authorities |
| Employees on record | 486 |
| Business units | 6 |
| Total delivered value | ~₹5,530 crore |

**687 documents, 20 types, ~39 MB.** 678 PDFs and 9 Excel workbooks, in `documents/`, grouped by type:
- `completion_certificate` (155) / `company_completion_certificate` (155)
- `reference_letter` (132)
- `performance_bond` (60)
- `personnel_certificate` (48)
- `cv` (39)
- `compliance_matrix` (40)
- `general_ledger_book` (8), `bank_statement` (8), `financial_statement` (7)
- `ra_bill` / `final_ra_bill` (12), `tender_dossier` (6), `iso_certificate` (5)
- `annual_report` (2), `past_performance_portfolio` (1)
- `workbooks` (.xlsx) (9)

---

## 📏 Official Scoring Formula

$$score = \max\left(0, 1 - \frac{|\text{your answer} - \text{correct answer}|}{\text{correct answer}}\right)$$

* Exact answer scores **1.00**
* 1% off scores **0.99**
* 5% off scores **0.95**
* 50% off scores **0.50**
* 100% off or worse scores **0.00**

---

## 🛡️ Rules
- All company entities and identifiers (CIN, GST, PAN) are synthetic and intentionally fail check digits.
- Everything needed to answer all 333 questions is contained in `documents/`.
- Final answers must be submitted as CSV with columns `question_id,answer`.
