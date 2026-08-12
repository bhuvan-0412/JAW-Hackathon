# Entities Extraction Schema

This document defines the schema for the per-document extracted JSON output stored in `extracted/{doc_id}.json`.

## Standard Top-Level Document Wrapper

Every document JSON output follows this standard structure:

```json
{
  "doc_id": "DOC-CC-001",
  "doc_type": "completion_certificate",
  "filename": "completion_certificate/DOC-CC-001.pdf",
  "size_bytes": 118743,
  "char_count": 3520,
  "page_count": 3,
  "extraction_warnings": [],
  "extracted_data": { ... }
}
```

---

## Field Schemas by Document Type

### 1. `completion_certificate` / `company_completion_certificate`
- `project_name` (string | null): Title of the project or work executed.
- `package_code` (string | null): Official package code or reference identifier (e.g. `WB-BR-029`, `Gujarat Pkg-1`).
- `client_name` (string | null): Commissioning client / authority name.
- `contract_value` (float | null): Contract or executed value in Rupees (parsed via `money_parser`).
- `raw_contract_value` (string | null): Original raw text string of the contract value.
- `start_date` (string | null): Commencement / start date (YYYY-MM-DD or raw string).
- `completion_date` (string | null): Date of work completion.
- `project_lead` (string | null): Contractor's project manager / lead engineer name.
- `grading_text` (string | null): Verbatim sentence containing the client's assessment / performance grading.

### 2. `reference_letter`
- `project_name` (string | null): Project title referenced.
- `package_code` (string | null): Package code referenced.
- `issuing_client` (string | null): Client issuing the recommendation / reference letter.
- `contract_value` (float | null): Stated contract value in Rupees.
- `completion_date` (string | null): Stated completion date.
- `recommendation_summary` (string | null): Summary / verbatim excerpt of the reference.

### 3. `performance_bond`
- `project_name` (string | null): Associated project / work name.
- `package_code` (string | null): Package code.
- `issuing_bank` (string | null): Bank issuing the guarantee.
- `beneficiary` (string | null): Client / employer beneficiary.
- `guarantee_amount` (float | null): Bond / guarantee amount in Rupees.
- `raw_guarantee_amount` (string | null): Raw guarantee string.
- `issue_date` (string | null): Bond issuance date.
- `expiry_date` (string | null): Bond validity / expiration date.

### 4. `personnel_certificate`
- `engineer_name` (string | null): Name of the certified employee / engineer.
- `employee_id` (string | null): Employee identifier (e.g. `EMP-001`).
- `certification_type` (string | null): Credential title (e.g. `PMP`, `Six Sigma Black Belt`).
- `credential_id` (string | null): License or credential ID.
- `issue_date` (string | null): Date of issuance.
- `expiry_date` (string | null): Expiration date / valid through date.

### 5. `cv`
- `engineer_name` (string | null): Full name of the engineer.
- `employee_id` (string | null): Employee ID.
- `designation` (string | null): Title / role in company.
- `total_experience` (string | null): Total years of experience.
- `projects_led` (list[object]): List of project records led or delivered by the engineer:
  - `project_name` (string | null)
  - `package_code` (string | null)
  - `client` (string | null)
  - `role` (string | null)

### 6. `ra_bill` / `final_ra_bill`
- `project_name` (string | null): Project title.
- `package_code` (string | null): Package code or contract reference number.
- `client_name` (string | null): Employer / client name.
- `bill_number` (string | null): Bill identifier.
- `bill_date` (string | null): Bill issuance date.
- `contract_value` (float | null): Contract / awarded value in Rupees.
- `billed_value` (float | null): Total billed value / amount in Rupees.
- `boq_items` (list[object]): Extracted BOQ line items:
  - `item_no` (string | null)
  - `description` (string | null)
  - `unit` (string | null)
  - `rate` (float | null)
  - `qty` (float | null)
  - `amount` (float | null)

### 7. `workbooks` (`boq_workbook`, `ageing_workbook`, `asset_register_workbook`, `trial_balance_workbook`)
- `workbook_type` (string): Type of workbook.
- `sheets` (dict[str, object]): Data extracted sheet-by-sheet:
  - `headers` (list[str]): Column headers.
  - `rows` (list[dict | list]): Table rows.
  - `unresolved_formulas` (list[str]): Any formula cells where cached value was missing and formula evaluation required fallback or warning.
