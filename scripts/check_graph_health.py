#!/usr/bin/env python3
"""
scripts/check_graph_health.py — Audits SQLite entity database connectivity, record counts, and link integrity.
"""

import sys
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import REFERENCE_DB_PATH
from src.reference_engine.entity_store import EntityStore


def check_graph_health():
    print("\n" + "=" * 65)
    print("  ROLE B ENTITY GRAPH / DATABASE HEALTH CHECK")
    print("=" * 65)

    store = EntityStore()
    cursor = store.conn.cursor()

    tables = [
        "documents",
        "projects",
        "reference_letters",
        "personnel_certifications",
        "engineers_cv",
        "performance_bonds",
        "ra_bills"
    ]

    print("  Table Record Counts:")
    print("  " + "-" * 40)
    for tbl in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            cnt = cursor.fetchone()[0]
            print(f"    * {tbl:28s}: {cnt:5d} records")
        except Exception as e:
            print(f"    * {tbl:28s}: ERROR ({e})")

    # Audit key linkages
    cursor.execute("SELECT COUNT(DISTINCT client_name) FROM projects WHERE client_name IS NOT NULL")
    unique_clients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT project_lead) FROM projects WHERE project_lead IS NOT NULL")
    unique_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT engineer_name) FROM personnel_certifications WHERE engineer_name IS NOT NULL")
    unique_certified_engineers = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE contract_value > 0")
    projects_with_value = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects WHERE completion_date IS NOT NULL")
    projects_with_date = cursor.fetchone()[0]

    print("\n  Graph Linkage Metrics:")
    print(f"    * Unique Clients Mapped:       {unique_clients}")
    print(f"    * Unique Project Leads:        {unique_leads}")
    print(f"    * Certified Engineers Mapped:  {unique_certified_engineers}")
    print(f"    * Projects with Parsed Value:  {projects_with_value}")
    print(f"    * Projects with Parsed Date:   {projects_with_date}")

    print("=" * 65 + "\n")
    return unique_clients > 0 and projects_with_value > 0


if __name__ == "__main__":
    ok = check_graph_health()
    sys.exit(0 if ok else 1)
