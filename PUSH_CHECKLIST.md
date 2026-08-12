# Pre-Push Release Readiness Checklist (Role D)

Use this checklist before pushing code or submitting deliverables to the team repository.

---

## 📋 Verification Checklist

- [ ] **1. Clean Environment Dependency Test**
  ```bash
  pip install -r requirements.txt
  ```

- [ ] **2. Automated Unit Tests Pass**
  ```bash
  python -m unittest discover -s tests -p "test_*.py"
  ```

- [ ] **3. Scorer Math Self-Test Verified**
  ```bash
  python evaluate.py --self-test
  python score_submission.py --self-test
  ```

- [ ] **4. Sample Score Calibration Runs Successfully**
  ```bash
  python scripts/run_sample_score.py
  ```

- [ ] **5. Full Pipeline Smoke Test Succeeds**
  ```bash
  python scripts/full_pipeline_check.py
  ```

- [ ] **6. Final Submission Generated**
  ```bash
  python run_harness.py --mode e2e --out submissions/final_submission.csv
  ```

- [ ] **7. Strict Submission Integrity Validation Passed**
  ```bash
  python validate_submission.py --submission submissions/final_submission.csv --report reports/VALIDATION_REPORT.md
  ```
  * [ ] Correct `question_id,answer` header
  * [ ] Exactly 333 unique QIDs present
  * [ ] Numeric answers only (no currency symbols, commas, or text)
  * [ ] Zero duplicate rows
  * [ ] Zero missing questions
  * [ ] Percentage values in $[0, 100]$, days non-negative

- [ ] **8. Release Manifest Frozen & Archived**
  ```bash
  python scripts/freeze_submission.py --submission submissions/final_submission.csv
  ```
  * [ ] `submissions/final_submission.manifest.json` exists
  * [ ] Timestamped copy saved in `submissions/archive/`

- [ ] **9. Reports Generated & Reviewed**
  * [ ] `reports/VALIDATION_REPORT.md`
  * [ ] `reports/EVALUATION_REPORT.md`

- [ ] **10. Working Tree Cleanliness**
  ```bash
  git status
  ```
  * [ ] No stray debug files or untracked cache artifacts
  * [ ] All core files staged for commit
