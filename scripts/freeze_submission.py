#!/usr/bin/env python3
"""
scripts/freeze_submission.py — Release manifest generator and submission freezer.
Validates submission, computes SHA256, records Git commit, writes manifest, and archives copy.

Usage:
    python scripts/freeze_submission.py
    python scripts/freeze_submission.py --submission submissions/final_submission.csv
"""

import sys
import json
import hashlib
import datetime
import shutil
import subprocess
import argparse
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

from src.config import QUESTIONS_PATH, OUTPUTS_DIR
from src.validation.validator import SubmissionValidator


def get_git_commit() -> str:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR)
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return "unknown"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def count_csv_rows(filepath: Path) -> int:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return max(0, len(lines) - 1)  # excluding header


def main():
    parser = argparse.ArgumentParser(description="Freeze and archive verified submission with manifest.")
    parser.add_argument("--submission", default=str(OUTPUTS_DIR / "final_submission.csv"), help="Submission CSV path")
    parser.add_argument("--questions", default=str(QUESTIONS_PATH), help="Questions path")
    args = parser.parse_args()

    sub_path = Path(args.submission)
    if not sub_path.exists():
        print(f"Error: Submission file {sub_path} does not exist.")
        sys.exit(1)

    print("\n" + "=" * 65)
    print("  FREEZING SUBMISSION RELEASE")
    print("=" * 65)

    # 1. Validate submission
    validator = SubmissionValidator(questions_path=args.questions)
    val_res = validator.validate(sub_path)
    print(f"  Submission File:       {sub_path.name}")
    status_badge = "[PASSED]" if val_res.is_valid else "[FAILED]"
    print(f"  Validator Status:      {status_badge}")

    if not val_res.is_valid:
        print("  [!] Error: Cannot freeze an invalid submission.")
        sys.exit(1)

    # 2. Compute metadata
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit_hash = get_git_commit()
    sha256_hash = compute_sha256(sub_path)
    rows_count = count_csv_rows(sub_path)

    manifest_data = {
        "timestamp": now_utc,
        "git_commit": commit_hash,
        "submission_file": sub_path.name,
        "rows": rows_count,
        "sha256": sha256_hash,
        "validator_passed": val_res.is_valid
    }

    # 3. Write manifest
    manifest_path = sub_path.parent / f"{sub_path.stem}.manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"  Manifest Generated:    {manifest_path}")

    # 4. Archive copy
    archive_dir = sub_path.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp_slug = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_sub_path = archive_dir / f"{sub_path.stem}_{timestamp_slug}.csv"
    archive_manifest_path = archive_dir / f"{sub_path.stem}_{timestamp_slug}.manifest.json"

    shutil.copy2(sub_path, archive_sub_path)
    shutil.copy2(manifest_path, archive_manifest_path)

    print(f"  Archived Copy:         {archive_sub_path}")
    print(f"  SHA256 Checksum:       {sha256_hash}")
    print(f"  Rows Count:            {rows_count}")
    print(f"  Git Commit:            {commit_hash}")
    print("=" * 65 + "\n")
    print("Release frozen and archived successfully!")


if __name__ == "__main__":
    main()
