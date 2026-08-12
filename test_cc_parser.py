#!/usr/bin/env python3
import fitz
import glob
import re
import json
from dateutil import parser as dt_parser
from money_parser import parse_money, find_money_mentions

MONTH_MAP = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}

def parse_date_string(s):
    if not s:
        return None
    s = s.replace('\n', ' ').strip()
    # YYYY-MM-DD
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', s)
    if m:
        return m.group(1)
    # DD/MM/YYYY
    m = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', s)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    # Month DD, YYYY or DD Month YYYY
    m = re.search(r'\b([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\b', s)
    if m and m.group(1).lower() in MONTH_MAP:
        mon = MONTH_MAP[m.group(1).lower()]
        day = int(m.group(2))
        yr = int(m.group(3))
        return f"{yr}-{mon:02d}-{day:02d}"
    m = re.search(r'\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b', s)
    if m and m.group(2).lower() in MONTH_MAP:
        mon = MONTH_MAP[m.group(2).lower()]
        day = int(m.group(1))
        yr = int(m.group(3))
        return f"{yr}-{mon:02d}-{day:02d}"
    try:
        dt = dt_parser.parse(s, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None

def parse_cc(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    lines = [line.strip() for line in full_text.split("\n") if line.strip()]
    
    # 1. Client Name: Line 1 of PDF text
    client_name = lines[0] if lines else None
    if client_name and any(kw in client_name.lower() for kw in ["certificate", "government of", "no.", "ref:"]):
        client_name = None

    # 2. Project Name & Package Code
    project_name = None
    package_code = None
    
    for i, l in enumerate(lines):
        if l.lower() in ("name of work", "particulars of the work"):
            if i + 1 < len(lines) and not lines[i+1].lower().startswith("nature"):
                project_name = lines[i+1]
                break
                
    if not project_name:
        m = re.search(r'work of\s+[“"]([^”"]+)[”"]', full_text, re.IGNORECASE)
        if m:
            project_name = m.group(1).strip()

    if project_name:
        project_name = re.sub(r'\s*\([^)]*\)$', '', project_name).strip()
        m = re.search(r'(?:Pkg|Package)[- ]?([A-Za-z0-9-]+)', project_name, re.IGNORECASE)
        if m:
            package_code = f"Pkg-{m.group(1)}"

    # 3. Category
    category = None
    for i, l in enumerate(lines):
        if "nature / category" in l.lower() or "category" in l.lower():
            if i + 1 < len(lines):
                category = lines[i+1]
                break
    if not category:
        m = re.search(r'\((\b[a-z\s]+\b)\)', full_text)
        if m:
            category = m.group(1).strip()

    # 4. Contract Value
    contract_value = None
    for i, l in enumerate(lines):
        if "contract value" in l.lower() or "executed value" in l.lower():
            if i + 1 < len(lines):
                contract_value = parse_money(lines[i+1])
                if contract_value:
                    break
    if contract_value is None:
        m = re.search(r'executed value of\s+([^(\n]+(?:\([^)]+\))?)', full_text, re.IGNORECASE)
        if m:
            contract_value = parse_money(m.group(1))
    if contract_value is None:
        mentions = find_money_mentions(full_text)
        if mentions:
            contract_value = mentions[0][1]

    # 5. Completion Date
    completion_date = None
    for i, l in enumerate(lines):
        if l.lower() in ("completion date", "actual completion date"):
            if i + 1 < len(lines):
                cand = parse_date_string(lines[i+1])
                if cand:
                    completion_date = cand
                    break
    if not completion_date:
        m = re.search(r'completed\s+(?:in all respects\s+)?on\s*([\s\S]{1,60}?)(?:at a gross|at a total|\.|,|\n\n|the work)', full_text, re.IGNORECASE)
        if m:
            cand = parse_date_string(m.group(1))
            if cand:
                completion_date = cand

    if not completion_date:
        m = re.search(r'completed\s+on\s+([^\n]+)', full_text, re.IGNORECASE)
        if m:
            completion_date = parse_date_string(m.group(1))

    # 6. Project Lead
    project_lead = None
    for i, l in enumerate(lines):
        if "contractor" in l.lower() and "manager" in l.lower():
            if i + 1 < len(lines) and len(lines[i+1]) < 40 and not lines[i+1].lower().startswith("national"):
                project_lead = lines[i+1]
                break
    if not project_lead:
        m = re.search(r'supervised on the contractor\'s side by\s+([A-Z][A-Za-z\s]+?)\.', full_text)
        if m:
            project_lead = m.group(1).strip()
    if not project_lead:
        for i, l in enumerate(lines):
            if l.lower() == "project manager" and i + 1 < len(lines) and "national infra" in lines[i+1].lower():
                if i - 1 >= 0:
                    project_lead = lines[i-1]
                    break

    return {
        "client_name": client_name,
        "project_name": project_name,
        "package_code": package_code,
        "category": category,
        "contract_value": contract_value,
        "completion_date": completion_date,
        "project_lead": project_lead
    }

if __name__ == "__main__":
    cc_pdfs = sorted(glob.glob("documents/completion_certificate/*.pdf"))
    missing_c, missing_p, missing_v, missing_d, missing_l = 0, 0, 0, 0, 0
    for p in cc_pdfs:
        res = parse_cc(p)
        if not res["client_name"]: missing_c += 1
        if not res["project_name"]: missing_p += 1
        if not res["contract_value"]: missing_v += 1
        if not res["completion_date"]: missing_d += 1
        if not res["project_lead"]: missing_l += 1

    print(f"Total CCs tested: {len(cc_pdfs)}")
    print(f"Missing client_name: {missing_c}")
    print(f"Missing project_name: {missing_p}")
    print(f"Missing contract_value: {missing_v}")
    print(f"Missing completion_date: {missing_d}")
    print(f"Missing project_lead: {missing_l}")
