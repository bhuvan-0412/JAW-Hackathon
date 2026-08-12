"""
src/config.py — Central configuration re-exporter and helper utilities.
"""

import sys
from pathlib import Path

# Add root directory to python path if needed
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from harness_config import (
    WORKSPACE_DIR,
    DOCUMENTS_DIR,
    EXTRACTED_DIR,
    DOCUMENT_INDEX_PATH,
    QUESTIONS_PATH,
    SAMPLE_QUESTIONS_PATH,
    OFFICIAL_EVALUATE_SCRIPT,
    SAMPLE_SUBMISSION_PATH,
    CACHE_DIR,
    REPORTS_DIR,
    OUTPUTS_DIR,
    REFERENCE_DB_PATH,
    COMPANY_METADATA,
    VALIDATION_BOUNDS,
)
