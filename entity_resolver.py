"""
entity_resolver.py — Generalizable Entity Resolution Engine

Implements resolve_entity(mention: str, entity_type: str = "client", question_text: str = "", conn=None) -> Optional[str]

Layer 1: Deterministic domain normalization & generic token composition (generic expansions only: PWD, PHED, Govt, Dept, Corp, Co, states).
Layer 2: Dynamic rapidfuzz token_set_ratio matching against entities.json / DB canonical entities.
Layer 3: Package & Engineer Lead Graph Linkage Fallback.
Layer 4: Local vLLM json_schema disambiguation via LLM_BASE_URL (when layers 1-3 are inconclusive).
"""

import os
import re
import json
import sqlite3
import requests
from typing import Optional, List

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None

# Layer 1: Generic, domain-standard expansions ONLY (justifiable as generic domain knowledge, not question-derived)
GENERIC_DOMAIN_ABBREVIATIONS = {
    r'\bpwd\b': 'public works department',
    r'\bpw\b': 'public works department',
    r'\bphed\b': 'public health engineering department',
    r'\bpheg\b': 'public health engineering department',
    r'\bgovt\b': 'government',
    r'\bdept\b': 'department',
    r'\bcorp\b': 'corporation',
    r'\bco\b': 'company',
    r'\bra\b': 'running account',
    r'\bexp\b': 'expressway',
    r'\bdev\b': 'development',
    r'\bauth\b': 'authority',
    r'\birrig\b': 'irrigation',
    r'\bgen\b': 'generation',
    r'\beng\b': 'engineering',
}

STATE_SYNONYMS = {
    'u p': 'uttar pradesh',
    'u.p.': 'uttar pradesh',
    'up': 'uttar pradesh',
    'm p': 'madhya pradesh',
    'm.p.': 'madhya pradesh',
    'mp': 'madhya pradesh',
    't n': 'tamil nadu',
    't.n.': 'tamil nadu',
    'tn': 'tamil nadu',
    'w b': 'west bengal',
    'w.b.': 'west bengal',
    'wb': 'west bengal',
    'mah': 'maharashtra',
}

LLM_BASE_URL = os.environ.get("LLM_BASE_URL")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen3.6-35b-a3b-nvfp4")

FUZZY_CONFIDENCE_THRESHOLD = 78  # Layer 2 threshold

_LLM_AVAILABLE = None

def check_llm_available() -> bool:
    global _LLM_AVAILABLE
    if _LLM_AVAILABLE is not None:
        return _LLM_AVAILABLE
    if not LLM_BASE_URL:
        _LLM_AVAILABLE = False
        return False
    try:
        r = requests.get(f"{LLM_BASE_URL.rstrip('/')}/models", timeout=0.3)
        _LLM_AVAILABLE = (r.status_code == 200)
    except Exception:
        _LLM_AVAILABLE = False
    return _LLM_AVAILABLE


def normalize_mention(text: str) -> str:
    """
    Layer 1: Lowercase, strip punctuation, collapse whitespace, expand domain-generic abbreviations.
    """
    if not text:
        return ""
    s = text.lower()
    for pat, repl in GENERIC_DOMAIN_ABBREVIATIONS.items():
        s = re.sub(pat, repl, s)
    for pat, repl in STATE_SYNONYMS.items():
        s = re.sub(r'\b' + re.escape(pat) + r'\b', repl, s)
    s = re.sub(r'[^\w\s]', ' ', s)
    return ' '.join(s.split())


def get_canonical_entities(entity_type: str = "client", conn=None) -> List[str]:
    """
    Dynamically fetch real entity names from entities.json or SQLite database at runtime.
    """
    entities_path = "entities.json"
    if os.path.exists(entities_path):
        try:
            with open(entities_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if entity_type == "client":
                clients = list(data.get("clients", {}).keys())
                if clients:
                    return sorted(clients, key=lambda x: len(x), reverse=True)
            elif entity_type == "engineer":
                engineers = list(data.get("engineers", {}).keys())
                if engineers:
                    return sorted(engineers, key=lambda x: len(x), reverse=True)
            elif entity_type == "project":
                projects = list(data.get("projects", {}).keys())
                if projects:
                    return sorted(projects, key=lambda x: len(x), reverse=True)
        except Exception:
            pass

    if conn:
        c = conn.cursor()
        if entity_type == "client":
            rows = c.execute("SELECT DISTINCT client_name FROM completion_certificates WHERE client_name IS NOT NULL").fetchall()
            return sorted([r[0] for r in rows], key=lambda x: len(x), reverse=True)
        elif entity_type == "engineer":
            r1 = [r[0] for r in c.execute("SELECT DISTINCT engineer_name FROM personnel_certificates WHERE engineer_name IS NOT NULL").fetchall()]
            r2 = [r[0] for r in c.execute("SELECT DISTINCT project_lead FROM completion_certificates WHERE project_lead IS NOT NULL").fetchall()]
            return sorted(list(set(r1 + r2)), key=lambda x: len(x), reverse=True)

    return []


def llm_disambiguate(mention: str, question_text: str, candidates: List[str]) -> Optional[str]:
    """
    Layer 4: Call vLLM endpoint with json_schema for structured disambiguation.
    """
    if not candidates or not check_llm_available():
        return None

    schema = {
        "type": "object",
        "properties": {
            "match": {"type": ["string", "null"], "enum": candidates + [None]}
        },
        "required": ["match"]
    }

    prompt = (
        f"Question: {question_text or mention}\n\n"
        f"Which of these canonical entities does the mention '{mention}' refer to?\n"
        f"Candidates: {candidates}\n"
        f"Return null if none are a confident match."
    )

    try:
        url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
        resp = requests.post(url, json={
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,  # Generous token allocation for Qwen reasoning trace
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "match", "schema": schema}
            }
        }, timeout=2.0)

        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            result = json.loads(content).get("match")
            if result in candidates:
                return result
    except Exception:
        pass

    return None


def resolve_entity(mention: str, entity_type: str = "client", question_text: str = "", conn=None, stats_tracker=None) -> Optional[str]:
    """
    Generalizable Entity Resolver:
      Layer 1: Deterministic Domain Normalization
      Layer 2: RapidFuzz Fuzzy String Matching
      Layer 3: Package Code & Engineer Lead Graph Linkage
      Layer 4: LLM Disambiguation via LLM_BASE_URL
    """
    if not mention:
        return None

    canonical_entities = get_canonical_entities(entity_type=entity_type, conn=conn)
    if not canonical_entities:
        return None

    norm_mention = normalize_mention(mention)
    norm_qtext = normalize_mention(question_text or mention)

    # Layer 1: Substring / Exact Normalized Match
    for ent in canonical_entities:
        ent_norm = normalize_mention(ent)
        if ent_norm in norm_qtext or ent_norm in norm_mention:
            if stats_tracker is not None:
                stats_tracker["layer1"] = stats_tracker.get("layer1", 0) + 1
            return ent

    # Layer 2: RapidFuzz Fuzzy Token Set Ratio Matching
    scored_candidates = []
    if fuzz:
        for ent in canonical_entities:
            ent_norm = normalize_mention(ent)
            ent_words = set(re.findall(r'\b[a-z]{3,}\b', ent_norm)) - {"government", "department", "corporation", "company", "limited", "authority", "office"}
            q_words = set(re.findall(r'\b[a-z]{3,}\b', norm_qtext)) - {"government", "department", "corporation", "company", "limited", "authority", "office"}

            overlap = len(ent_words & q_words)
            if overlap >= 1:
                score = fuzz.token_set_ratio(ent_norm, norm_qtext)
                if score >= 60:
                    scored_candidates.append((ent, score + overlap * 5))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)

    if scored_candidates:
        top_cand, top_score = scored_candidates[0]
        if top_score >= FUZZY_CONFIDENCE_THRESHOLD:
            if len(scored_candidates) == 1 or (top_score - scored_candidates[1][1] >= 5):
                if stats_tracker is not None:
                    stats_tracker["layer2"] = stats_tracker.get("layer2", 0) + 1
                return top_cand

    # Layer 3: Package Code & Engineer Lead Graph Linkage Fallback
    if conn:
        c = conn.cursor()
        # 3a. Check package code regex
        m_pkg = re.search(r'\bpkg[\s\-]*(\d+)\b', norm_qtext, re.IGNORECASE)
        if m_pkg:
            pkg_code = f"Pkg-{m_pkg.group(1)}"
            r = c.execute("SELECT client_name FROM completion_certificates WHERE LOWER(package_code) = LOWER(?) AND client_name IS NOT NULL", (pkg_code,)).fetchone()
            if r and r[0]:
                if stats_tracker is not None:
                    stats_tracker["layer3"] = stats_tracker.get("layer3", 0) + 1
                return r[0]

        # 3b. Check engineer lead name regex
        engineers = get_canonical_entities(entity_type="engineer", conn=conn)
        for eng in engineers:
            first_name = eng.split()[0].lower()
            if len(first_name) >= 4 and re.search(r'\b' + re.escape(first_name) + r'\b', norm_qtext):
                r = c.execute("SELECT client_name FROM completion_certificates WHERE LOWER(project_lead) LIKE LOWER(?) AND client_name IS NOT NULL", (f"%{first_name}%",)).fetchone()
                if r and r[0]:
                    if stats_tracker is not None:
                        stats_tracker["layer3"] = stats_tracker.get("layer3", 0) + 1
                    return r[0]

    # Layer 4: LLM Disambiguation (when layers 1-3 are inconclusive)
    shortlist = [c[0] for c in scored_candidates[:5]] if scored_candidates else canonical_entities[:5]
    llm_match = llm_disambiguate(mention=mention, question_text=question_text, candidates=shortlist)
    if llm_match:
        if stats_tracker is not None:
            stats_tracker["layer4"] = stats_tracker.get("layer4", 0) + 1
        return llm_match

    # Fallback to top fuzzy candidate if score >= 65
    if scored_candidates and scored_candidates[0][1] >= 65:
        if stats_tracker is not None:
            stats_tracker["layer2"] = stats_tracker.get("layer2", 0) + 1
        return scored_candidates[0][0]

    return None
