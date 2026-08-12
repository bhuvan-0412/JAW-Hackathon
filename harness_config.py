#!/usr/bin/env python3
"""
harness_config.py — Central configuration for Role D Harness.
Defines base paths, expected dataset constants, scoring parameters, and validation bounds.
"""

import os
from pathlib import Path

# Base workspace directory
WORKSPACE_DIR = Path(__file__).resolve().parent

# Input paths
DOCUMENTS_DIR = WORKSPACE_DIR / "documents"
EXTRACTED_DIR = WORKSPACE_DIR / "extracted"
DOCUMENT_INDEX_PATH = WORKSPACE_DIR / "document_index.csv"
QUESTIONS_PATH = WORKSPACE_DIR / "questions.json"
SAMPLE_QUESTIONS_PATH = WORKSPACE_DIR / "sample_questions.json"
OFFICIAL_EVALUATE_SCRIPT = WORKSPACE_DIR / "evaluate.py"
SAMPLE_SUBMISSION_PATH = WORKSPACE_DIR / "sample_submission.csv"

# Output and cache paths
CACHE_DIR = WORKSPACE_DIR / ".harness_cache"
REPORTS_DIR = WORKSPACE_DIR / "reports"
OUTPUTS_DIR = WORKSPACE_DIR / "submissions"
REFERENCE_DB_PATH = CACHE_DIR / "bid_intelligence.db"

# Company-wide constraints (from hackathon briefing)
COMPANY_METADATA = {
    "name": "National Infrastructure Corp. Ltd.",
    "head_office": "Salt Lake, Kolkata",
    "founded_year": 2005,
    "completed_works_count": 155,
    "clients_count": 62,
    "employees_count": 486,
    "business_units_count": 6,
    "total_delivered_value_inr": 55_300_000_000.0,  # ~5,530 crore
    "total_documents_count": 687,
    "total_questions_count": 333,
    "sample_questions_count": 21,
}

# Validation Bounds
VALIDATION_BOUNDS = {
    "percent": {
        "min": 0.0,
        "max": 100.0,
        "precision": 2,  # round to 2 decimal places
    },
    "days": {
        "min": 0,
        "max": 365 * 50,  # 50 years max
        "must_be_integer": True,
    },
    "count": {
        "min": 0,
        "max": 10_000,
        "must_be_integer": True,
    },
    "money": {
        "min": 0.0,
        "max": 100_000_000_000.0,  # ₹10,000 crore max individual/aggregate
        "precision": 2,
    }
}

# Ensure required directories exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
