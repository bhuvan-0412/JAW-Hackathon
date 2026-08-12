"""
src/reference_engine/entity_store.py — SQLite-backed Unified Entity Store.
Integrates extracted documents into a normalized relational database with multi-hop query helpers.
"""

import os
import json
import sqlite3
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple

from src.config import EXTRACTED_DIR, DOCUMENT_INDEX_PATH, REFERENCE_DB_PATH


class EntityStore:
    """
    Unified relational entity store bridging Role A extracted data into a queryable SQLite database.
    """

    def __init__(self, db_path: Union[str, Path] = REFERENCE_DB_PATH, auto_build: bool = True):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        if auto_build and self._is_empty():
            self.build_from_extracted()

    def _init_schema(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            doc_type TEXT,
            filename TEXT,
            size_bytes INTEGER,
            page_count INTEGER,
            char_count INTEGER
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT,
            project_name TEXT,
            package_code TEXT,
            client_name TEXT,
            contract_value REAL,
            raw_contract_value TEXT,
            start_date TEXT,
            completion_date TEXT,
            project_lead TEXT,
            grading_text TEXT,
            doc_type TEXT,
            UNIQUE(doc_id, project_name)
        );

        CREATE TABLE IF NOT EXISTS reference_letters (
            doc_id TEXT PRIMARY KEY,
            project_name TEXT,
            package_code TEXT,
            issuing_client TEXT,
            contract_value REAL,
            completion_date TEXT,
            recommendation_summary TEXT
        );

        CREATE TABLE IF NOT EXISTS personnel_certifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id TEXT,
            engineer_name TEXT,
            employee_id TEXT,
            certification_type TEXT,
            credential_id TEXT,
            issue_date TEXT,
            expiry_date TEXT
        );

        CREATE TABLE IF NOT EXISTS engineers_cv (
            doc_id TEXT PRIMARY KEY,
            engineer_name TEXT,
            employee_id TEXT,
            designation TEXT,
            total_experience TEXT,
            qualification TEXT
        );

        CREATE TABLE IF NOT EXISTS performance_bonds (
            doc_id TEXT PRIMARY KEY,
            project_name TEXT,
            package_code TEXT,
            issuing_bank TEXT,
            beneficiary TEXT,
            guarantee_amount REAL,
            issue_date TEXT,
            expiry_date TEXT
        );

        CREATE TABLE IF NOT EXISTS ra_bills (
            doc_id TEXT PRIMARY KEY,
            project_name TEXT,
            package_code TEXT,
            client_name TEXT,
            bill_number TEXT,
            bill_date TEXT,
            contract_value REAL,
            billed_value REAL
        );

        CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_name);
        CREATE INDEX IF NOT EXISTS idx_projects_lead ON projects(project_lead);
        CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(project_name);
        CREATE INDEX IF NOT EXISTS idx_projects_pkg ON projects(package_code);
        CREATE INDEX IF NOT EXISTS idx_pcert_name ON personnel_certifications(engineer_name);
        CREATE INDEX IF NOT EXISTS idx_ref_client ON reference_letters(issuing_client);
        """)
        self.conn.commit()

    def _is_empty(self) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        return cursor.fetchone()[0] == 0

    def build_from_extracted(self, extracted_dir: Union[str, Path] = EXTRACTED_DIR):
        """
        Ingest all extracted/*.json files and populate the relational tables.
        """
        extracted_dir = Path(extracted_dir)
        if not extracted_dir.exists():
            return

        cursor = self.conn.cursor()

        # Ingest each extracted file
        for json_file in extracted_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            doc_id = data.get("doc_id")
            doc_type = data.get("doc_type")
            ext_data = data.get("extracted_data") or {}

            if not doc_id:
                continue

            # Insert into documents table
            cursor.execute("""
                INSERT OR REPLACE INTO documents (doc_id, doc_type, filename, size_bytes, page_count, char_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                doc_type,
                data.get("filename"),
                data.get("size_bytes"),
                data.get("page_count"),
                data.get("char_count")
            ))

            # Insert by doc_type
            if doc_type in ("completion_certificate", "company_completion_certificate"):
                cursor.execute("""
                    INSERT OR REPLACE INTO projects (
                        doc_id, project_name, package_code, client_name,
                        contract_value, raw_contract_value, start_date, completion_date,
                        project_lead, grading_text, doc_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    ext_data.get("project_name"),
                    ext_data.get("package_code"),
                    ext_data.get("client_name"),
                    ext_data.get("contract_value"),
                    ext_data.get("raw_contract_value"),
                    ext_data.get("start_date"),
                    ext_data.get("completion_date"),
                    ext_data.get("project_lead"),
                    ext_data.get("grading_text"),
                    doc_type
                ))

            elif doc_type == "reference_letter":
                cursor.execute("""
                    INSERT OR REPLACE INTO reference_letters (
                        doc_id, project_name, package_code, issuing_client,
                        contract_value, completion_date, recommendation_summary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    ext_data.get("project_name"),
                    ext_data.get("package_code"),
                    ext_data.get("issuing_client"),
                    ext_data.get("contract_value"),
                    ext_data.get("completion_date"),
                    ext_data.get("recommendation_summary")
                ))

            elif doc_type == "personnel_certificate":
                cursor.execute("""
                    INSERT INTO personnel_certifications (
                        doc_id, engineer_name, employee_id, certification_type,
                        credential_id, issue_date, expiry_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    ext_data.get("engineer_name"),
                    ext_data.get("employee_id"),
                    ext_data.get("certification_type"),
                    ext_data.get("credential_id"),
                    ext_data.get("issue_date"),
                    ext_data.get("expiry_date")
                ))

            elif doc_type == "cv":
                cursor.execute("""
                    INSERT OR REPLACE INTO engineers_cv (
                        doc_id, engineer_name, employee_id, designation,
                        total_experience, qualification
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    ext_data.get("engineer_name"),
                    ext_data.get("employee_id"),
                    ext_data.get("designation"),
                    ext_data.get("total_experience"),
                    ext_data.get("qualification")
                ))

            elif doc_type == "performance_bond":
                cursor.execute("""
                    INSERT OR REPLACE INTO performance_bonds (
                        doc_id, project_name, package_code, issuing_bank,
                        beneficiary, guarantee_amount, issue_date, expiry_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    ext_data.get("project_name"),
                    ext_data.get("package_code"),
                    ext_data.get("issuing_bank"),
                    ext_data.get("beneficiary"),
                    ext_data.get("guarantee_amount"),
                    ext_data.get("issue_date"),
                    ext_data.get("expiry_date")
                ))

            elif doc_type in ("ra_bill", "final_ra_bill"):
                cursor.execute("""
                    INSERT OR REPLACE INTO ra_bills (
                        doc_id, project_name, package_code, client_name,
                        bill_number, bill_date, contract_value, billed_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    ext_data.get("project_name"),
                    ext_data.get("package_code"),
                    ext_data.get("client_name"),
                    ext_data.get("bill_number"),
                    ext_data.get("bill_date"),
                    ext_data.get("contract_value"),
                    ext_data.get("billed_value")
                ))

        self.conn.commit()

    # --- Query API ---

    def get_all_clients(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT client_name FROM projects WHERE client_name IS NOT NULL AND client_name != ''")
        return [row[0] for row in cursor.fetchall()]

    def find_client_fuzzy(self, name_query: str) -> Optional[str]:
        if not name_query:
            return None
        cleaned = name_query.strip().lower()
        clients = self.get_all_clients()
        # Exact substring
        for c in clients:
            if cleaned in c.lower() or c.lower() in cleaned:
                return c
        return None

    def get_client_projects(self, client_name: str) -> List[dict]:
        """
        Returns deduplicated projects for a given client (prioritizing completion_certificate over company_completion_certificate).
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM projects
            WHERE client_name LIKE ?
            ORDER BY contract_value DESC
        """, (f"%{client_name}%",))
        rows = [dict(r) for r in cursor.fetchall()]

        # Deduplicate projects by normalized project_name or package_code
        deduped = {}
        for r in rows:
            p_name = (r.get("project_name") or "").strip().lower()
            pkg = (r.get("package_code") or "").strip().lower()
            key = p_name if p_name else pkg
            if not key:
                continue
            if key not in deduped:
                deduped[key] = r
            else:
                # Prefer completion_certificate over company_completion_certificate
                if r.get("doc_type") == "completion_certificate":
                    deduped[key] = r
        return list(deduped.values())

    def get_projects_by_engineer(self, engineer_name: str) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM projects
            WHERE project_lead LIKE ?
            ORDER BY completion_date
        """, (f"%{engineer_name}%",))
        rows = [dict(r) for r in cursor.fetchall()]
        deduped = {}
        for r in rows:
            p_name = (r.get("project_name") or "").strip().lower()
            if p_name and p_name not in deduped:
                deduped[p_name] = r
        return list(deduped.values())

    def get_engineer_certifications(self, engineer_name: str, cert_type: Optional[str] = None) -> List[dict]:
        cursor = self.conn.cursor()
        if cert_type:
            cursor.execute("""
                SELECT * FROM personnel_certifications
                WHERE engineer_name LIKE ? AND certification_type LIKE ?
                ORDER BY issue_date
            """, (f"%{engineer_name}%", f"%{cert_type}%"))
        else:
            cursor.execute("""
                SELECT * FROM personnel_certifications
                WHERE engineer_name LIKE ?
                ORDER BY issue_date
            """, (f"%{engineer_name}%",))
        return [dict(r) for r in cursor.fetchall()]

    def get_reference_letter_count_for_client(self, client_name: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(DISTINCT project_name) FROM reference_letters
            WHERE issuing_client LIKE ?
        """, (f"%{client_name}%",))
        return cursor.fetchone()[0]

    def close(self):
        self.conn.close()
