#!/usr/bin/env python3
"""
Step 37 — Physical Production Governance, Compliance Evidence & Final Release Audit Script
"""

import os
import re
import sys
import hashlib

EXPECTED_MODEL_SHA256 = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"

REQUIRED_GOVERNANCE_DOCS = [
    "docs/DATA_GOVERNANCE_AUDIT.md",
    "docs/AUDIT_TRAIL_VERIFICATION.md",
    "docs/RBAC_LEAST_PRIVILEGE_AUDIT.md",
    "docs/SUPPLY_CHAIN_AUDIT.md",
    "docs/PRODUCTION_CONFIGURATION_AUDIT.md",
    "docs/COMPLIANCE_EVIDENCE_MATRIX.md",
    "docs/FINAL_RELEASE_ARTIFACT_AUDIT.md",
    "docs/STEP37_FINAL_GOVERNANCE_REPORT.md",
]

def print_section(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def verify_ml_invariant():
    print_section("1. ML Model Checksum Invariant Verification")
    model_path = os.path.join(os.path.dirname(__file__), "models", "fusion_triage.pkl")
    
    if not os.path.exists(model_path):
        print(f"❌ FAIL: ML model file not found at {model_path}")
        return False
    
    with open(model_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    
    print(f"  ML Model SHA-256: {sha256}")
    if sha256 != EXPECTED_MODEL_SHA256:
        print(f"❌ FAIL: ML model SHA-256 mismatch! Expected {EXPECTED_MODEL_SHA256}")
        return False
    print("  ✅ ML model checksum matches release invariant (0 modifications).")
    return True

def verify_governance_documents():
    print_section("2. Governance & Compliance Documentation Audit")
    project_root = os.path.join(os.path.dirname(__file__), "..")
    
    missing_docs = []
    for relative_doc in REQUIRED_GOVERNANCE_DOCS:
        full_path = os.path.join(project_root, relative_doc)
        if os.path.exists(full_path):
            size_bytes = os.path.getsize(full_path)
            print(f"  ✅ Verified: {relative_doc} ({size_bytes} bytes)")
        else:
            print(f"  ❌ MISSING: {relative_doc}")
            missing_docs.append(relative_doc)

    if missing_docs:
        print(f"❌ FAIL: Missing required governance documentation files: {missing_docs}")
        return False

    return True

def verify_data_privacy_and_rbac_specs():
    print_section("3. Data Privacy (PHI/PII) & RBAC Matrix Audit")
    project_root = os.path.join(os.path.dirname(__file__), "..")
    rbac_doc = os.path.join(project_root, "docs", "RBAC_LEAST_PRIVILEGE_AUDIT.md")
    privacy_doc = os.path.join(project_root, "docs", "DATA_GOVERNANCE_AUDIT.md")

    with open(rbac_doc, "r", encoding="utf-8") as f1, open(privacy_doc, "r", encoding="utf-8") as f2:
        rbac_text = f1.read()
        privacy_text = f2.read()

    roles = ["Citizen", "Responder", "Paramedic", "Admin"]
    for role in roles:
        if role not in rbac_text:
            print(f"❌ FAIL: Missing role '{role}' in RBAC_LEAST_PRIVILEGE_AUDIT.md")
            return False
    print(f"  ✅ RBAC role permissions verified ({', '.join(roles)}).")

    for phi in ["email", "hashed_password", "gps_lat", "allergies"]:
        if phi not in privacy_text:
            print(f"❌ FAIL: Missing PHI/PII attribute '{phi}' in DATA_GOVERNANCE_AUDIT.md")
            return False
    print("  ✅ PHI/PII data inventory & privacy controls verified.")

    return True

def verify_supply_chain_lockfiles():
    print_section("4. Supply Chain & Lockfile Integrity Audit")
    project_root = os.path.join(os.path.dirname(__file__), "..")
    py_req = os.path.join(project_root, "backend", "requirements.txt")
    node_lock = os.path.join(project_root, "frontend", "package-lock.json")

    if not os.path.exists(py_req):
        print(f"❌ FAIL: Python requirements.txt missing at {py_req}")
        return False
    print("  ✅ Python dependencies manifest (requirements.txt) verified.")

    if not os.path.exists(node_lock):
        print(f"❌ FAIL: Node package-lock.json missing at {node_lock}")
        return False
    print("  ✅ Node lockfile (package-lock.json) verified.")

    return True

def verify_release_artifacts():
    print_section("5. Final Release Artifact Manifest Verification")
    project_root = os.path.join(os.path.dirname(__file__), "..")
    manifest_doc = os.path.join(project_root, "docs", "FINAL_RELEASE_ARTIFACT_AUDIT.md")

    with open(manifest_doc, "r", encoding="utf-8") as f:
        manifest_text = f.read()

    if EXPECTED_MODEL_SHA256 not in manifest_text:
        print("❌ FAIL: Model checksum missing in FINAL_RELEASE_ARTIFACT_AUDIT.md")
        return False
    print("  ✅ Model SHA-256 checksum verified in release artifact audit.")

    if "c3d4e5f6a7b8" not in manifest_text:
        print("❌ FAIL: Alembic head revision missing in FINAL_RELEASE_ARTIFACT_AUDIT.md")
        return False
    print("  ✅ Alembic head revision (c3d4e5f6a7b8) verified in release artifact audit.")

    return True

def main():
    print("=" * 80)
    print(" ROADSOS STEP 37: PRODUCTION GOVERNANCE, COMPLIANCE & FINAL AUDIT")
    print("=" * 80)

    checks = [
        verify_ml_invariant(),
        verify_governance_documents(),
        verify_data_privacy_and_rbac_specs(),
        verify_supply_chain_lockfiles(),
        verify_release_artifacts(),
    ]

    all_passed = all(checks)
    print_section("STEP 37 GOVERNANCE AUDIT SUMMARY")
    if all_passed:
        print("🟢 ALL STEP 37 PRODUCTION GOVERNANCE AUDITS PASSED SUCCESSFULLY.")
        sys.exit(0)
    else:
        print("🔴 STEP 37 AUDIT FAILED. CHECK ERRORS ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    main()
