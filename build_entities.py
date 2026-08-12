#!/usr/bin/env python3
"""
build_entities.py — Entity Resolution & Knowledge Graph Construction Pipeline

Performs entity resolution across all extracted document JSON files in extracted/*.
Builds top-level entities:
  - projects[]
  - clients[]
  - engineers[]
  - documents[]

Outputs:
  - entities.json (The unified knowledge graph)
  - needs_review.jsonl (Audit log for ambiguous entity resolution decisions)
"""

import os
import re
import json
import glob
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXTRACTED_DIR = os.path.join(BASE_DIR, 'extracted')
ENTITIES_OUTPUT = os.path.join(BASE_DIR, 'entities.json')
NEEDS_REVIEW_OUTPUT = os.path.join(BASE_DIR, 'needs_review.jsonl')


def normalize_package_code(pkg_raw: str, proj_name_raw: str = None) -> str:
    """
    Extract and normalize package codes across documents.
    Handles variations like:
      - 'Pkg-115'
      - 'Jharkhand Pkg-115'
      - 'Package 115'
      - 'WB-BR-029'
      - 'Pkg - 107'
      - 'Ring Road — Uttar Pradesh Pkg-107'
    """
    targets = [t for t in [pkg_raw, proj_name_raw] if t and isinstance(t, str)]
    if not targets:
        return None

    for target in targets:
        # Match custom contract codes like WB-BR-029
        match_custom = re.search(r'\b([A-Z]{2}-[A-Z]{2}-\d+)\b', target)
        if match_custom:
            return match_custom.group(1).strip()

        # Match Pkg-XXX or Package XXX or State Pkg-XXX
        match = re.search(r'\b(?:Pkg|Package)[- ]?([A-Za-z0-9]+)\b', target, re.IGNORECASE)
        if match:
            code_num = match.group(1).strip()
            if len(code_num) == 1 and not code_num.isdigit():
                continue
            return f"Pkg-{code_num}"

    return None


def normalize_client_name(client_raw: str) -> tuple[str, str]:
    """
    Normalize client names to a canonical form and return (canonical_name, normalization_key).
    Strips trailing entity types like (psu), (Government), (Private).
    Filters generic letterhead lines or contractor company names.
    Standardizes 'Corp' -> 'Corporation', 'Dept' -> 'Department'.
    """
    if not client_raw or not isinstance(client_raw, str):
        return None, None

    cleaned = client_raw.strip()
    cleaned_lower = cleaned.lower()

    if any(kw in cleaned_lower for kw in ['national infrastructure corp', 'government of india / state authority', 'issued under the provisions']):
        return None, None
    
    # Remove parens like (psu), (Government), (Private), (govt)
    cleaned_no_paren = re.sub(r'\s*\((?:psu|government|private|govt)\)', '', cleaned, flags=re.IGNORECASE).strip()

    # Standardize common abbreviations
    norm = cleaned_no_paren
    norm = re.sub(r'\bCorp\b', 'Corporation', norm, flags=re.IGNORECASE)
    norm = re.sub(r'\bDept\b', 'Department', norm, flags=re.IGNORECASE)
    norm = re.sub(r'\bGovt\b', 'Government', norm, flags=re.IGNORECASE)
    
    # Standardize comma spacing
    norm = re.sub(r'\s*,\s*', ', ', norm)
    norm = re.sub(r'\s+', ' ', norm).strip()

    # Normalization key for grouping
    norm_key = norm.lower().replace(',', '').replace('&', 'and')
    norm_key = re.sub(r'\s+', ' ', norm_key).strip()

    return norm, norm_key


class EntityGraphBuilder:
    def __init__(self, extracted_dir: str):
        self.extracted_dir = extracted_dir
        self.raw_docs = []
        self.needs_review_logs = []
        self.normalization_logs = []

    def load_extractions(self):
        json_files = glob.glob(os.path.join(self.extracted_dir, '*.json'))
        for fpath in json_files:
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    doc = json.load(f)
                    self.raw_docs.append(doc)
            except Exception as e:
                print(f"Error reading {fpath}: {e}")

    def build_graph(self) -> dict:
        self.load_extractions()

        projects_map = {}  # pkg_code -> dict
        clients_registry = {}  # client_key -> dict
        engineers_map = {}  # eng_name_lower -> dict
        doc_resolution_list = []

        # Client normalization mapping tracking
        client_key_to_canonical = {}

        # 1. First Pass: Group projects by normalized package code from completion certificates and bonds/letters/bills
        for doc in self.raw_docs:
            doc_id = doc.get("doc_id")
            doc_type = doc.get("doc_type")
            ext_data = doc.get("extracted_data", {})
            
            raw_pkg = ext_data.get("package_code")
            raw_proj_name = ext_data.get("project_name")
            
            # Extract package code if applicable
            norm_pkg = normalize_package_code(raw_pkg, raw_proj_name)
            
            # Log package code normalization if raw_pkg differed from norm_pkg
            if raw_pkg and norm_pkg and raw_pkg != norm_pkg:
                self.normalization_logs.append({
                    "doc_id": doc_id,
                    "field": "package_code",
                    "raw": raw_pkg,
                    "normalized": norm_pkg
                })

            # Process completion certificates & company completion certificates to seed projects
            if doc_type in ("completion_certificate", "company_completion_certificate"):
                # Fallback to doc_id index if norm_pkg is not found
                if not norm_pkg and doc_id:
                    m_num = re.search(r'DOC-C{2,3}-(\d+)', doc_id)
                    if m_num:
                        norm_pkg = f"Pkg-{int(m_num.group(1))}"

                if norm_pkg:
                    if norm_pkg not in projects_map:
                        projects_map[norm_pkg] = {
                            "package_code": norm_pkg,
                            "raw_package_codes": set(),
                            "project_name": raw_proj_name or norm_pkg,
                            "client_raw_names": set(),
                            "contract_value": None,
                            "start_date": None,
                            "completion_date": None,
                            "project_lead": None,
                            "grading_text": None,
                            "documents": [],
                            "has_reference_letter": False,
                            "has_performance_bond": False
                        }
                    
                    p = projects_map[norm_pkg]
                    if raw_pkg:
                        p["raw_package_codes"].add(raw_pkg)
                    if raw_proj_name and (not p["project_name"] or len(raw_proj_name) > len(p["project_name"])):
                        p["project_name"] = raw_proj_name
                    
                    client_raw = ext_data.get("client_name")
                    if client_raw:
                        p["client_raw_names"].add(client_raw)

                    val = ext_data.get("contract_value")
                    if val and (p["contract_value"] is None or val > p["contract_value"]):
                        p["contract_value"] = val

                    start_d = ext_data.get("start_date")
                    if start_d and not p["start_date"]:
                        p["start_date"] = start_d

                    comp_d = ext_data.get("completion_date")
                    if comp_d and not p["completion_date"]:
                        p["completion_date"] = comp_d

                    lead = ext_data.get("project_lead")
                    if lead and not p["project_lead"]:
                        p["project_lead"] = lead

                    grading = ext_data.get("grading_text")
                    if grading and not p["grading_text"]:
                        p["grading_text"] = grading

                    if doc_id not in p["documents"]:
                        p["documents"].append(doc_id)

        # 2. Second Pass: Associate reference letters, performance bonds, RA bills, and other docs with projects
        for doc in self.raw_docs:
            doc_id = doc.get("doc_id")
            doc_type = doc.get("doc_type")
            ext_data = doc.get("extracted_data", {})
            resolved = False
            resolved_pkg = None

            raw_pkg = ext_data.get("package_code")
            raw_proj_name = ext_data.get("project_name")
            norm_pkg = normalize_package_code(raw_pkg, raw_proj_name)

            if doc_type in ("completion_certificate", "company_completion_certificate"):
                if not norm_pkg and doc_id:
                    m_num = re.search(r'DOC-C{2,3}-(\d+)', doc_id)
                    if m_num:
                        norm_pkg = f"Pkg-{int(m_num.group(1))}"
                resolved = True
                resolved_pkg = norm_pkg

            elif doc_type == "reference_letter":
                client_raw = ext_data.get("issuing_client")
                if not norm_pkg and doc_id:
                    m_num = re.search(r'DOC-REF-(\d+)', doc_id)
                    if m_num:
                        norm_pkg = f"Pkg-{int(m_num.group(1))}"

                if norm_pkg:
                    if norm_pkg not in projects_map:
                        projects_map[norm_pkg] = {
                            "package_code": norm_pkg,
                            "raw_package_codes": set(),
                            "project_name": raw_proj_name or norm_pkg,
                            "client_raw_names": set(),
                            "contract_value": ext_data.get("contract_value"),
                            "start_date": None,
                            "completion_date": ext_data.get("completion_date"),
                            "project_lead": None,
                            "grading_text": None,
                            "documents": [],
                            "has_reference_letter": True,
                            "has_performance_bond": False
                        }
                    else:
                        projects_map[norm_pkg]["has_reference_letter"] = True

                    projects_map[norm_pkg]["has_reference_letter"] = True
                    if client_raw:
                        projects_map[norm_pkg]["client_raw_names"].add(client_raw)
                    if doc_id not in projects_map[norm_pkg]["documents"]:
                        projects_map[norm_pkg]["documents"].append(doc_id)
                    resolved = True
                    resolved_pkg = norm_pkg

            elif doc_type == "performance_bond":
                client_raw = ext_data.get("beneficiary")
                if not norm_pkg and doc_id:
                    m_num = re.search(r'DOC-BOND-(\d+)', doc_id)
                    if m_num:
                        norm_pkg = f"Pkg-{int(m_num.group(1))}"

                if norm_pkg:
                    if norm_pkg not in projects_map:
                        projects_map[norm_pkg] = {
                            "package_code": norm_pkg,
                            "raw_package_codes": set(),
                            "project_name": raw_proj_name or norm_pkg,
                            "client_raw_names": set(),
                            "contract_value": None,
                            "start_date": ext_data.get("issue_date"),
                            "completion_date": ext_data.get("expiry_date"),
                            "project_lead": None,
                            "grading_text": None,
                            "documents": [],
                            "has_reference_letter": False,
                            "has_performance_bond": True
                        }
                    else:
                        projects_map[norm_pkg]["has_performance_bond"] = True

                    projects_map[norm_pkg]["has_performance_bond"] = True
                    if client_raw:
                        projects_map[norm_pkg]["client_raw_names"].add(client_raw)
                    if doc_id not in projects_map[norm_pkg]["documents"]:
                        projects_map[norm_pkg]["documents"].append(doc_id)
                    resolved = True
                    resolved_pkg = norm_pkg

            elif doc_type in ("ra_bill", "final_ra_bill"):
                client_raw = ext_data.get("client_name")
                if norm_pkg and norm_pkg in projects_map:
                    if client_raw:
                        projects_map[norm_pkg]["client_raw_names"].add(client_raw)
                    if doc_id not in projects_map[norm_pkg]["documents"]:
                        projects_map[norm_pkg]["documents"].append(doc_id)
                    resolved = True
                    resolved_pkg = norm_pkg

            elif doc_type in ("cv", "personnel_certificate"):
                resolved = True
                # Engineers resolved in engineer linking step

            doc_resolution_list.append({
                "doc_id": doc_id,
                "doc_type": doc_type,
                "filename": doc.get("filename"),
                "resolved": resolved,
                "resolved_package_code": resolved_pkg
            })

        # 3. Client Name Resolution & Registry Construction
        # Group raw client names across projects into canonical Client entities
        raw_to_canonical = {}
        for pkg, proj in projects_map.items():
            for raw_client in proj["client_raw_names"]:
                canon_name, norm_key = normalize_client_name(raw_client)
                if not canon_name:
                    continue
                
                if norm_key not in clients_registry:
                    client_id = f"CLIENT-{len(clients_registry) + 1:03d}"
                    clients_registry[norm_key] = {
                        "client_id": client_id,
                        "canonical_name": canon_name,
                        "name_variants": set([raw_client]),
                        "projects": [],
                        "total_completed_works": 0
                    }
                else:
                    clients_registry[norm_key]["name_variants"].add(raw_client)

                raw_to_canonical[raw_client] = clients_registry[norm_key]

        # Link projects to client entities
        for pkg, proj in projects_map.items():
            assigned_client = None
            for raw_client in proj["client_raw_names"]:
                if raw_client in raw_to_canonical:
                    assigned_client = raw_to_canonical[raw_client]
                    break
            
            if assigned_client:
                proj["client_id"] = assigned_client["client_id"]
                proj["client_name"] = assigned_client["canonical_name"]
                if pkg not in assigned_client["projects"]:
                    assigned_client["projects"].append(pkg)
                    assigned_client["total_completed_works"] += 1
            else:
                proj["client_id"] = None
                proj["client_name"] = None

        # Check for potential ambiguous client merges to populate needs_review.jsonl
        client_keys = list(clients_registry.keys())
        for i in range(len(client_keys)):
            for j in range(i + 1, len(client_keys)):
                c1 = clients_registry[client_keys[i]]
                c2 = clients_registry[client_keys[j]]
                # Simple substring overlap check between canonical names
                n1, n2 = c1["canonical_name"].lower(), c2["canonical_name"].lower()
                words1 = set(n1.split())
                words2 = set(n2.split())
                overlap = words1.intersection(words2) - {"dept", "department", "corp", "corporation", "limited", "ltd", "of", "and", "&", "the"}
                if len(overlap) >= 2 and n1 != n2:
                    self.needs_review_logs.append({
                        "entity_type": "client",
                        "candidate_1": c1["canonical_name"],
                        "candidate_2": c2["canonical_name"],
                        "common_words": list(overlap),
                        "status": "kept_separate_pending_review"
                    })

        # 4. Engineer Entity Resolution & Linking
        for doc in self.raw_docs:
            doc_id = doc.get("doc_id")
            doc_type = doc.get("doc_type")
            ext_data = doc.get("extracted_data", {})

            eng_name = ext_data.get("engineer_name") or ext_data.get("project_lead")
            if not eng_name or not isinstance(eng_name, str):
                continue
            
            eng_key = eng_name.strip().lower()
            if eng_key not in engineers_map:
                engineers_map[eng_key] = {
                    "engineer_name": eng_name.strip(),
                    "employee_id": ext_data.get("employee_id"),
                    "certifications": [],
                    "projects_led": [],
                    "documents": []
                }

            eng_record = engineers_map[eng_key]
            if doc_id not in eng_record["documents"]:
                eng_record["documents"].append(doc_id)

            if ext_data.get("employee_id") and not eng_record["employee_id"]:
                eng_record["employee_id"] = ext_data.get("employee_id")

            if doc_type == "personnel_certificate":
                cert_info = {
                    "certification_type": ext_data.get("certification_type"),
                    "credential_id": ext_data.get("credential_id"),
                    "issue_date": ext_data.get("issue_date"),
                    "expiry_date": ext_data.get("expiry_date"),
                    "doc_id": doc_id
                }
                if cert_info not in eng_record["certifications"]:
                    eng_record["certifications"].append(cert_info)

            elif doc_type == "cv":
                for proj in ext_data.get("projects_led", []):
                    pkg_raw = proj.get("package_code")
                    proj_name_raw = proj.get("project_name")
                    norm_p = normalize_package_code(pkg_raw, proj_name_raw)
                    if norm_p and norm_p not in eng_record["projects_led"]:
                        eng_record["projects_led"].append(norm_p)

        # Also link project_lead from completion certificates to engineers_map
        for pkg, proj in projects_map.items():
            lead_name = proj.get("project_lead")
            if lead_name and isinstance(lead_name, str):
                eng_key = lead_name.strip().lower()
                if eng_key in engineers_map:
                    if pkg not in engineers_map[eng_key]["projects_led"]:
                        engineers_map[eng_key]["projects_led"].append(pkg)

        # Format output structures
        projects_list = []
        for pkg, proj in sorted(projects_map.items()):
            proj["raw_package_codes"] = list(proj["raw_package_codes"])
            proj["client_raw_names"] = list(proj["client_raw_names"])
            projects_list.append(proj)

        clients_list = []
        for key, client in sorted(clients_registry.items()):
            client["name_variants"] = list(client["name_variants"])
            clients_list.append(client)

        engineers_list = list(engineers_map.values())

        graph = {
            "metadata": {
                "total_projects": len(projects_list),
                "total_clients": len(clients_list),
                "total_engineers": len(engineers_list),
                "total_documents": len(doc_resolution_list)
            },
            "projects": projects_list,
            "clients": clients_list,
            "engineers": engineers_list,
            "documents": doc_resolution_list
        }

        return graph

    def save_outputs(self, graph: dict):
        with open(ENTITIES_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2)
        print(f"Saved entity graph to {ENTITIES_OUTPUT}")

        with open(NEEDS_REVIEW_OUTPUT, 'w', encoding='utf-8') as f:
            for item in self.needs_review_logs:
                f.write(json.dumps(item) + '\n')
        print(f"Saved ambiguous review logs to {NEEDS_REVIEW_OUTPUT}")


if __name__ == '__main__':
    print("Building entity resolution graph...")
    builder = EntityGraphBuilder(EXTRACTED_DIR)
    graph = builder.build_graph()
    builder.save_outputs(graph)
    print("\n--- SUMMARY STATISTICS ---")
    print(f"Projects resolved: {graph['metadata']['total_projects']}")
    print(f"Clients resolved: {graph['metadata']['total_clients']}")
    print(f"Engineers resolved: {graph['metadata']['total_engineers']}")
    print(f"Documents tracked: {graph['metadata']['total_documents']}")
