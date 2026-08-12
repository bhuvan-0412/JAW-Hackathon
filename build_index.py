#!/usr/bin/env python3
"""
build_index.py — Compiles all document estate data into SQLite database estate_index.db
"""

import os
import re
import glob
import json
import sqlite3
import datetime
import fitz
import openpyxl
from dateutil import parser as dt_parser
from money_parser import parse_money, find_money_mentions, parse_cell_value

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCUMENTS_DIR = os.path.join(BASE_DIR, 'documents')
DB_PATH = os.path.join(BASE_DIR, 'estate_index.db')

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
    m = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', s)
    if m:
        return m.group(1)
    m = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', s)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    try:
        dt = dt_parser.parse(s, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return None

def clean_client_name(cname, lines):
    if not cname:
        return None
    cname = cname.strip()
    if any(kw in cname.lower() for kw in ["certificate", "government of india", "no.", "ref:", "dated"]):
        return None
    if len(lines) > 1 and (cname.endswith("West") or cname.endswith("of") or cname.endswith("Govt") or cname.endswith("&") or cname.endswith("Dept,")):
        cname = cname + " " + lines[1]
    
    if cname.isupper():
        words = cname.split()
        cname = " ".join(w.capitalize() if len(w) > 3 else w for w in words)
    return cname.strip()

def init_db(conn):
    c = conn.cursor()
    c.executescript('''
        DROP TABLE IF EXISTS completion_certificates;
        DROP TABLE IF EXISTS reference_letters;
        DROP TABLE IF EXISTS performance_bonds;
        DROP TABLE IF EXISTS personnel_certificates;
        DROP TABLE IF EXISTS cvs;
        DROP TABLE IF EXISTS cv_projects;
        DROP TABLE IF EXISTS ra_bills;
        DROP TABLE IF EXISTS ageing_records;
        
        CREATE TABLE completion_certificates (
            doc_id TEXT PRIMARY KEY,
            doc_type TEXT,
            project_name TEXT,
            package_code TEXT,
            client_name TEXT,
            category TEXT,
            contract_value REAL,
            start_date TEXT,
            completion_date TEXT,
            project_lead TEXT,
            grading_text TEXT,
            raw_text TEXT
        );

        CREATE TABLE reference_letters (
            doc_id TEXT PRIMARY KEY,
            project_name TEXT,
            package_code TEXT,
            issuing_client TEXT,
            contract_value REAL,
            completion_date TEXT,
            raw_text TEXT
        );

        CREATE TABLE performance_bonds (
            doc_id TEXT PRIMARY KEY,
            project_name TEXT,
            package_code TEXT,
            issuing_bank TEXT,
            beneficiary TEXT,
            guarantee_amount REAL,
            issue_date TEXT,
            expiry_date TEXT,
            raw_text TEXT
        );

        CREATE TABLE personnel_certificates (
            doc_id TEXT PRIMARY KEY,
            engineer_name TEXT,
            employee_id TEXT,
            certification_type TEXT,
            credential_id TEXT,
            issue_date TEXT,
            expiry_date TEXT,
            raw_text TEXT
        );

        CREATE TABLE cvs (
            doc_id TEXT PRIMARY KEY,
            engineer_name TEXT,
            employee_id TEXT,
            designation TEXT,
            total_experience TEXT,
            raw_text TEXT
        );

        CREATE TABLE cv_projects (
            cv_doc_id TEXT,
            engineer_name TEXT,
            project_name TEXT,
            package_code TEXT,
            client TEXT,
            role TEXT
        );

        CREATE TABLE ra_bills (
            doc_id TEXT PRIMARY KEY,
            doc_type TEXT,
            project_name TEXT,
            package_code TEXT,
            client_name TEXT,
            bill_number TEXT,
            bill_date TEXT,
            contract_value REAL,
            billed_value REAL,
            raw_text TEXT
        );

        CREATE TABLE ageing_records (
            doc_id TEXT,
            client_name TEXT,
            project_name TEXT,
            billed_amount REAL,
            collected_amount REAL,
            outstanding_amount REAL
        );
        
        CREATE INDEX idx_cc_client ON completion_certificates(client_name);
        CREATE INDEX idx_cc_pkg ON completion_certificates(package_code);
        CREATE INDEX idx_cc_lead ON completion_certificates(project_lead);
        CREATE INDEX idx_ref_pkg ON reference_letters(package_code);
        CREATE INDEX idx_ref_client ON reference_letters(issuing_client);
        CREATE INDEX idx_pc_eng ON personnel_certificates(engineer_name);
        CREATE INDEX idx_pc_cert ON personnel_certificates(certification_type);
        CREATE INDEX idx_cv_eng ON cvs(engineer_name);
        CREATE INDEX idx_cvp_eng ON cv_projects(engineer_name);
        CREATE INDEX idx_cvp_pkg ON cv_projects(package_code);
    ''')
    conn.commit()

def populate_db(conn):
    c = conn.cursor()
    
    # 1. Parse Completion Certificates
    cc_pdfs = glob.glob(os.path.join(DOCUMENTS_DIR, "completion_certificate", "*.pdf"))
    comp_cc_pdfs = glob.glob(os.path.join(DOCUMENTS_DIR, "company_completion_certificate", "*.pdf"))
    
    all_cc_pdfs = [(p, "completion_certificate") for p in cc_pdfs] + [(p, "company_completion_certificate") for p in comp_cc_pdfs]
    
    for pdf_path, d_type in all_cc_pdfs:
        doc_id = os.path.splitext(os.path.basename(pdf_path))[0]
        try:
            doc = fitz.open(pdf_path)
            full_text = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception:
            full_text = ""
            
        lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        
        # Client Name
        client_name = clean_client_name(lines[0] if lines else None, lines)

        # Project Name & Package Code
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

        # Category
        category = None
        for i, l in enumerate(lines):
            if "nature / category" in l.lower() or "category" in l.lower():
                if i + 1 < len(lines):
                    category = lines[i+1]
                    break
        if not category:
            m = re.search(r'\((buildings|bridges flyovers|water treatment|sewerage drainage|roads maintenance|tunnels|industrial epc|power infra|dam|drainage|large bridges|small buildings)\)', full_text, re.IGNORECASE)
            if m:
                category = m.group(1).strip()

        # Contract Value
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

        # Completion Date
        completion_date = None
        m_comp = re.search(r'completed\s+(?:in all respects\s+)?on\s*([A-Za-z]+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4})', full_text, re.IGNORECASE)
        if m_comp:
            completion_date = parse_date_string(m_comp.group(1))
            
        if not completion_date:
            for i, l in enumerate(lines):
                if l.lower() in ("completion date", "actual completion date"):
                    if i + 1 < len(lines):
                        cand = parse_date_string(lines[i+1])
                        if cand:
                            completion_date = cand
                            break

        # Project Lead
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

        # Grading text
        grading_text = None
        m = re.search(r'overall quality of the completed work is graded\s+([A-Za-z]+)', full_text, re.IGNORECASE)
        if m:
            grading_text = m.group(1).strip()

        c.execute('''
            INSERT OR REPLACE INTO completion_certificates 
            (doc_id, doc_type, project_name, package_code, client_name, category, contract_value, start_date, completion_date, project_lead, grading_text, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (doc_id, d_type, project_name, package_code, client_name, category, contract_value, None, completion_date, project_lead, grading_text, full_text))

    # 2. Parse Reference Letters
    ref_pdfs = glob.glob(os.path.join(DOCUMENTS_DIR, "reference_letter", "*.pdf"))
    for pdf_path in ref_pdfs:
        doc_id = os.path.splitext(os.path.basename(pdf_path))[0]
        try:
            doc = fitz.open(pdf_path)
            full_text = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception:
            full_text = ""
        lines = [l.strip() for l in full_text.split("\n") if l.strip()]

        issuing_client = clean_client_name(lines[0] if lines else None, lines)

        project_name = None
        package_code = None
        m = re.search(r'for the work\s+[“"]?([^”"\n]+?)[”"]?\s*\((INR|Rs)', full_text, re.IGNORECASE)
        if m:
            project_name = m.group(1).strip()
        if not project_name:
            for i, l in enumerate(lines):
                if l.lower() in ("name of work", "project title", "work"):
                    if i + 1 < len(lines):
                        project_name = lines[i+1]
                        break
        if project_name:
            m = re.search(r'(?:Pkg|Package)[- ]?([A-Za-z0-9-]+)', project_name, re.IGNORECASE)
            if m:
                package_code = f"Pkg-{m.group(1)}"

        contract_value = None
        mentions = find_money_mentions(full_text)
        if mentions:
            contract_value = mentions[0][1]

        completion_date = parse_date_string(full_text)

        c.execute('''
            INSERT OR REPLACE INTO reference_letters 
            (doc_id, project_name, package_code, issuing_client, contract_value, completion_date, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (doc_id, project_name, package_code, issuing_client, contract_value, completion_date, full_text))

    # 3. Parse Performance Bonds
    pb_pdfs = glob.glob(os.path.join(DOCUMENTS_DIR, "performance_bond", "*.pdf"))
    for pdf_path in pb_pdfs:
        doc_id = os.path.splitext(os.path.basename(pdf_path))[0]
        try:
            doc = fitz.open(pdf_path)
            full_text = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception:
            full_text = ""
        
        guarantee_amount = None
        mentions = find_money_mentions(full_text)
        if mentions:
            guarantee_amount = mentions[0][1]
            
        c.execute('''
            INSERT OR REPLACE INTO performance_bonds
            (doc_id, project_name, package_code, issuing_bank, beneficiary, guarantee_amount, issue_date, expiry_date, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (doc_id, None, None, None, None, guarantee_amount, None, None, full_text))

    # 4. Parse Personnel Certificates
    pc_pdfs = glob.glob(os.path.join(DOCUMENTS_DIR, "personnel_certificate", "*.pdf"))
    for pdf_path in pc_pdfs:
        doc_id = os.path.splitext(os.path.basename(pdf_path))[0]
        try:
            doc = fitz.open(pdf_path)
            full_text = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception:
            full_text = ""

        engineer_name = None
        m = re.search(r'certify that\s*\n+([A-Z][A-Za-z\s]+)', full_text, re.IGNORECASE)
        if m:
            engineer_name = m.group(1).strip()
        if not engineer_name:
            m = re.search(r'awarded to\s+([A-Z][A-Za-z\s]+)', full_text, re.IGNORECASE)
            if m:
                engineer_name = m.group(1).strip()

        employee_id = None
        m = re.search(r'Employee ID:\s*(EMP-[\d]+)', full_text, re.IGNORECASE)
        if m:
            employee_id = m.group(1).strip()

        cert_type = None
        if 'PMP' in full_text or 'Project Management Professional' in full_text:
            cert_type = 'PMP'
        elif 'Six Sigma' in full_text:
            cert_type = 'Six Sigma Black Belt'

        credential_id = None
        m = re.search(r'(?:Credential ID|License No|Registration No):\s*([A-Za-z0-9-]+)', full_text, re.IGNORECASE)
        if m:
            credential_id = m.group(1).strip()

        issue_date = None
        m = re.search(r'(?:Issued|Date of Issue):\s*([\d]{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|[A-Za-z]+\s+\d{1,2},\s*\d{4})', full_text, re.IGNORECASE)
        if m:
            issue_date = parse_date_string(m.group(1))

        expiry_date = None
        m = re.search(r'(?:Valid Through|Expiry Date):\s*([\d]{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|[A-Za-z]+\s+\d{1,2},\s*\d{4})', full_text, re.IGNORECASE)
        if m:
            expiry_date = parse_date_string(m.group(1))

        c.execute('''
            INSERT OR REPLACE INTO personnel_certificates 
            (doc_id, engineer_name, employee_id, certification_type, credential_id, issue_date, expiry_date, raw_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (doc_id, engineer_name, employee_id, cert_type, credential_id, issue_date, expiry_date, full_text))

    # 5. Parse CVs
    cv_pdfs = glob.glob(os.path.join(DOCUMENTS_DIR, "cv", "*.pdf"))
    for pdf_path in cv_pdfs:
        doc_id = os.path.splitext(os.path.basename(pdf_path))[0]
        try:
            doc = fitz.open(pdf_path)
            full_text = "\n".join(page.get_text() for page in doc)
            doc.close()
        except Exception:
            full_text = ""

        lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        engineer_name = None
        for i, l in enumerate(lines):
            if l.lower() in ("name", "full name", "curriculum vitae"):
                if i + 1 < len(lines):
                    engineer_name = lines[i+1]
                    break
        if not engineer_name and lines:
            engineer_name = lines[0].replace("CURRICULUM VITAE", "").strip()

        employee_id = None
        m = re.search(r'EMP-[\d]+', full_text)
        if m:
            employee_id = m.group(0)

        designation = None
        m = re.search(r'Designation:\s*([^\n]+)', full_text)
        if m:
            designation = m.group(1).strip()

        c.execute('''
            INSERT OR REPLACE INTO cvs 
            (doc_id, engineer_name, employee_id, designation, total_experience, raw_text)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (doc_id, engineer_name, employee_id, designation, None, full_text))

        project_matches = re.findall(r'(?:Project|Work):\s*([^\n]+?)\s*·\s*(Pkg-[\d\w-]+)', full_text)
        for proj, pkg in project_matches:
            c.execute('''
                INSERT INTO cv_projects (cv_doc_id, engineer_name, project_name, package_code, client, role)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (doc_id, engineer_name, proj.strip(), pkg.strip(), None, "Project Manager"))

    conn.commit()

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    populate_db(conn)
    
    c = conn.cursor()
    print("Database Index Population Complete:")
    print("  completion_certificates:", c.execute("SELECT COUNT(*) FROM completion_certificates").fetchone()[0])
    print("  reference_letters:", c.execute("SELECT COUNT(*) FROM reference_letters").fetchone()[0])
    print("  performance_bonds:", c.execute("SELECT COUNT(*) FROM performance_bonds").fetchone()[0])
    print("  personnel_certificates:", c.execute("SELECT COUNT(*) FROM personnel_certificates").fetchone()[0])
    print("  cvs:", c.execute("SELECT COUNT(*) FROM cvs").fetchone()[0])
    conn.close()
