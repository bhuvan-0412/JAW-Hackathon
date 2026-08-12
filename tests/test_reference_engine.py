"""
tests/test_reference_engine.py — Unit tests for EntityStore and BaselineSolver.
"""

import unittest
import sqlite3
from src.reference_engine.entity_store import EntityStore
from src.reference_engine.baseline_solver import BaselineSolver


class TestReferenceEngine(unittest.TestCase):

    def setUp(self):
        # Use an in-memory database for isolated unit testing
        self.store = EntityStore(db_path=":memory:", auto_build=False)
        self.store._init_schema()

        # Populate minimal dummy test data
        cursor = self.store.conn.cursor()
        cursor.execute("""
            INSERT INTO projects (doc_id, project_name, package_code, client_name, contract_value, completion_date, project_lead, doc_type)
            VALUES 
            ('CC-1', 'Highway — West Bengal Pkg-10', 'Pkg-10', 'Public Works Department, West Bengal', 500000000.0, '2022-05-15', 'Arun Kumar', 'completion_certificate'),
            ('CC-2', 'Bridge — West Bengal Pkg-11', 'Pkg-11', 'Public Works Department, West Bengal', 300000000.0, '2023-01-10', 'Arun Kumar', 'completion_certificate')
        """)
        cursor.execute("""
            INSERT INTO personnel_certifications (doc_id, engineer_name, certification_type, issue_date)
            VALUES ('PC-1', 'Arun Kumar', 'PMP', '2021-01-01')
        """)
        self.store.conn.commit()

        self.solver = BaselineSolver(self.store)

    def tearDown(self):
        self.store.close()

    def test_entity_store_query(self):
        projects = self.store.get_client_projects("Public Works Department, West Bengal")
        self.assertEqual(len(projects), 2)
        total_val = sum(p["contract_value"] for p in projects)
        self.assertEqual(total_val, 800_000_000.0)

    def test_baseline_solver_hop_aggregate(self):
        q = {
            "qid": "TEST-01",
            "question": "What is the total value of completed assignments for Public Works Department, West Bengal?",
            "answer_type": "money",
            "shape": "hop_aggregate"
        }
        ans = self.solver.solve_question(q)
        self.assertEqual(ans, 800_000_000.0)

    def test_baseline_solver_avg_work_size(self):
        q = {
            "qid": "TEST-02",
            "question": "What is the average size of work for Public Works Department, West Bengal?",
            "answer_type": "money",
            "shape": "avg_work_size"
        }
        ans = self.solver.solve_question(q)
        self.assertEqual(ans, 400_000_000.0)


if __name__ == "__main__":
    unittest.main()
