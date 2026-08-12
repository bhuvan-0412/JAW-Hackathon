"""
entity_resolver.py — Generalizable Entity Resolution Engine

Dynamically resolves informal, abbreviated, or misspelled entity mentions
in text (clients, engineers, projects) against canonical database entities.

Uses multi-stage resolution:
  1. Generic acronym expansion & text normalization
  2. Dynamic State + Department entity composition (State: Gujarat, MA, WB, etc. + Dept: PWD, PHED, Jal Nigam, etc.)
  3. Exact canonical string match
  4. Token set ratio / RapidFuzz / Difflib fuzzy similarity
  5. Package code & engineer lead graph linkage
  6. Local vLLM fallback for ambiguous mentions
"""

import os
import re
import sqlite3
import requests
from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz, process
except ImportError:
    fuzz = None
    process = None

ACRONYM_EXPANSIONS = {
    r'\bpwd\b': 'Public Works Department',
    r'\bpw\b': 'Public Works Department',
    r'\bphed\b': 'Public Health Engineering Dept',
    r'\bpheg\b': 'Public Health Engineering Dept',
    r'\bmah\b': 'Maharashtra',
    r'\bup\b': 'Uttar Pradesh',
    r'\bwb\b': 'West Bengal',
    r'\bmp\b': 'Madhya Pradesh',
    r'\btn\b': 'Tamil Nadu',
    r'\birr\b': 'Irrigation & Waterways Dept',
    r'\bneda\b': 'National Expressway Development Authority',
    r'\bmega infra authority\b': 'Mega Infrastructure Authority',
    r'\bmega infra\b': 'Mega Infrastructure Authority',
}

STATE_MAP = {
    'gujarat': 'Gujarat',
    'maharashtra': 'Maharashtra',
    'mah': 'Maharashtra',
    'west bengal': 'West Bengal',
    'wb': 'West Bengal',
    'tamil nadu': 'Tamil Nadu',
    'tn': 'Tamil Nadu',
    'rajasthan': 'Rajasthan',
    'uttar pradesh': 'Uttar Pradesh',
    'up': 'Uttar Pradesh',
    'jharkhand': 'Jharkhand',
    'odisha': 'Odisha',
    'madhya pradesh': 'Madhya Pradesh',
    'mp': 'Madhya Pradesh',
}


class GeneralizableEntityResolver:
    def __init__(self, db_path: str = "estate_index.db", llm_url: str | None = None):
        self.db_path = db_path
        self.llm_url = llm_url or os.environ.get("LLM_BASE_URL")
        self._canonical_clients = None
        self._canonical_engineers = None

    def _get_clients(self, conn) -> list[str]:
        if self._canonical_clients is None:
            c = conn.cursor()
            rows = c.execute("SELECT DISTINCT client_name FROM completion_certificates WHERE client_name IS NOT NULL").fetchall()
            self._canonical_clients = sorted([r[0] for r in rows], key=lambda x: len(x), reverse=True)
        return self._canonical_clients

    def _get_engineers(self, conn) -> list[str]:
        if self._canonical_engineers is None:
            c = conn.cursor()
            r1 = [r[0] for r in c.execute("SELECT DISTINCT engineer_name FROM personnel_certificates WHERE engineer_name IS NOT NULL").fetchall()]
            r2 = [r[0] for r in c.execute("SELECT DISTINCT project_lead FROM completion_certificates WHERE project_lead IS NOT NULL").fetchall()]
            self._canonical_engineers = sorted(list(set(r1 + r2)), key=lambda x: len(x), reverse=True)
        return self._canonical_engineers

    def normalize_text(self, text: str) -> str:
        s = text.lower()
        for pat, repl in ACRONYM_EXPANSIONS.items():
            s = re.sub(pat, repl.lower(), s)
        s = re.sub(r'[\,\-\.\;]', ' ', s)
        return ' '.join(s.split())

    def resolve_client(self, text: str, conn) -> str | None:
        if not text:
            return None

        clients = self._get_clients(conn)
        norm_text = self.normalize_text(text)
        text_l = text.lower()

        # Stage 1: Dynamic State + Department Composition
        found_state = None
        for st_k, st_v in STATE_MAP.items():
            if re.search(r'\b' + re.escape(st_k) + r'\b', text_l):
                found_state = st_v
                break

        if found_state:
            # Check department patterns
            if "public works" in norm_text or "pwd" in text_l or "pw" in text_l:
                target = f"Public Works Department, Govt of {found_state}"
                if target in clients: return target
            elif "public health" in norm_text or "phed" in text_l or "pheg" in text_l:
                target = f"Public Health Engineering Dept, {found_state}"
                if target in clients: return target
            elif "jal nigam" in norm_text:
                target = f"Jal Nigam, {found_state}"
                if target in clients: return target
            elif "irrigation" in norm_text:
                target = f"Irrigation & Waterways Dept, Govt of {found_state}"
                if target in clients: return target
            elif "municipal" in norm_text:
                target = f"{found_state} Municipal Corporation"
                if target in clients: return target

        # Stage 2: Exact / Normalized Substring Match
        for cl in clients:
            cl_l = cl.lower()
            cl_norm = self.normalize_text(cl)
            if cl_l in text_l or cl_norm in norm_text:
                return cl

        # Stage 3: Token Set / Fuzzy Similarity Matching
        best_match = None
        best_score = 0.0

        for cl in clients:
            cl_norm = self.normalize_text(cl)
            cl_words = set(re.findall(r'\b[a-z]{3,}\b', cl_norm)) - {"dept", "govt", "corp", "ltd", "and", "the", "inc", "department"}
            text_words = set(re.findall(r'\b[a-z]{3,}\b', norm_text)) - {"dept", "govt", "corp", "ltd", "and", "the", "inc", "department"}

            overlap = len(cl_words & text_words)
            if overlap >= 2 or (overlap == 1 and len(cl_words) <= 2):
                if fuzz:
                    score = fuzz.token_set_ratio(cl_norm, norm_text)
                else:
                    score = SequenceMatcher(None, cl_norm, norm_text).ratio() * 100

                if score > best_score and score >= 60:
                    best_score = score
                    best_match = cl

        if best_match:
            return best_match

        # Stage 4: Package Code Lookup Fallback
        m_pkg = re.search(r'\bpkg[\s\-]*(\d+)\b', text, re.IGNORECASE)
        if m_pkg:
            pkg_code = f"Pkg-{m_pkg.group(1)}"
            c = conn.cursor()
            r = c.execute("SELECT client_name FROM completion_certificates WHERE LOWER(package_code) = LOWER(?) AND client_name IS NOT NULL", (pkg_code,)).fetchone()
            if r:
                return r[0]

        # Stage 5: Engineer Lead Graph Fallback
        engineers = self._get_engineers(conn)
        for eng in engineers:
            first_name = eng.split()[0].lower()
            if len(first_name) >= 4 and first_name in text_l:
                c = conn.cursor()
                r = c.execute("SELECT client_name FROM completion_certificates WHERE LOWER(project_lead) LIKE LOWER(?) AND client_name IS NOT NULL", (f"%{first_name}%",)).fetchone()
                if r:
                    return r[0]

        # Stage 6: Local vLLM Fallback (if LLM endpoint available)
        if self.llm_url:
            try:
                prompt = f"Identify which client from this list {clients} is referenced in text: '{text}'. Return JSON: {{\"client\": \"canonical_name_or_null\"}}"
                res = requests.post(f"{self.llm_url}/chat/completions", json={
                    "model": os.environ.get("LLM_MODEL", "qwen3.6-35b-a3b-nvfp4"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0
                }, timeout=3)
                if res.status_code == 200:
                    data = res.json()
                    ans_text = data['choices'][0]['message']['content']
                    for cl in clients:
                        if cl.lower() in ans_text.lower():
                            return cl
            except Exception:
                pass

        return None
