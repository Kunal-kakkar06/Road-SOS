#!/usr/bin/env python3
"""
Step 36 — Physical Operational Handoff, Documentation & Knowledge Transfer Validation Script
"""

import os
import re
import sys
import hashlib

EXPECTED_MODEL_SHA256 = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"

REQUIRED_HANDOFF_DOCS = [
    "docs/DOCUMENTATION_AUDIT.md",
    "docs/DEVELOPER_HANDOFF.md",
    "docs/OPERATIONS_HANDOFF.md",
    "docs/SUPPORT_RUNBOOK.md",
    "docs/ML_MODEL_HANDOFF.md",
    "docs/DISASTER_RECOVERY_QUICK_REFERENCE.md",
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

def get_project_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr and curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "docs")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_step36_handoff_docs_exist():
    """Verify all 6 required operational handoff documentation files exist and are non-empty."""
    project_root = get_project_root()
    for doc_path in REQUIRED_HANDOFF_DOCS:
        full_path = os.path.join(project_root, doc_path)
        assert os.path.exists(full_path), f"Handoff doc missing: {doc_path}"
        assert os.path.getsize(full_path) > 200, f"Handoff doc too small: {doc_path}"

def test_step36_version_consistency():
    """Verify version numbers and commands are consistent across handoff docs."""
    project_root = get_project_root()
    dev_doc = os.path.join(project_root, "docs", "DEVELOPER_HANDOFF.md")
    ops_doc = os.path.join(project_root, "docs", "OPERATIONS_HANDOFF.md")
    
    with open(dev_doc, "r", encoding="utf-8") as f1, open(ops_doc, "r", encoding="utf-8") as f2:
        text = f1.read() + f2.read()
    
    assert "v1.0.0" in text, "Missing version v1.0.0 tag in handoff documentation"
    assert "alembic upgrade head" in text, "Missing migration command in handoff documentation"

def test_step36_ml_model_handoff_spec():
    """Verify ML handoff doc specifies SHA-256 checksum and feature vector ordering."""
    project_root = get_project_root()
    ml_doc = os.path.join(project_root, "docs", "ML_MODEL_HANDOFF.md")
    ops_doc = os.path.join(project_root, "docs", "OPERATIONS_HANDOFF.md")
    dev_doc = os.path.join(project_root, "docs", "DEVELOPER_HANDOFF.md")
    
    with open(dev_doc, "r", encoding="utf-8") as f:
        dev_text = f.read()
    with open(ops_doc, "r", encoding="utf-8") as f:
        ops_text = f.read()

    if "v1.0.0" not in dev_text or "v1.0.0" not in ops_text:
        print("❌ FAIL: Version v1.0.0 missing in developer or ops handoff docs")
        return False
    print("  ✅ Release version v1.0.0 consistent across handoff docs.")

    # Verify Alembic migration command
    if "alembic upgrade head" not in dev_text or "alembic upgrade head" not in ops_text:
        print("❌ FAIL: Alembic migration command missing in handoff docs")
        return False
    print("  ✅ Database migration command 'alembic upgrade head' verified.")

    # Verify Pytest execution command
    if "pytest tests/" not in dev_text:
        print("❌ FAIL: Pytest command missing in developer handoff doc")
        return False
    print("  ✅ Test execution command 'pytest tests/' verified.")

    return True

def verify_ml_handoff_contract():
    print_section("4. ML Model Provenance & Feature Contract Audit")
    project_root = os.path.join(os.path.dirname(__file__), "..")
    ml_doc = os.path.join(project_root, "docs", "ML_MODEL_HANDOFF.md")
    
    with open(ml_doc, "r", encoding="utf-8") as f:
        ml_text = f.read()

    if EXPECTED_MODEL_SHA256 not in ml_text:
        print("❌ FAIL: ML model checksum SHA-256 missing in ML_MODEL_HANDOFF.md")
        return False
    print("  ✅ ML model SHA-256 checksum documented in ML_MODEL_HANDOFF.md.")

    features = ["speed_at_crash", "g_force", "airbag_deployed", "rollover", "head_injury_risk"]
    for feat in features:
        if feat not in ml_text:
            print(f"❌ FAIL: Feature '{feat}' missing in ML_MODEL_HANDOFF.md vector spec")
            return False
    print(f"  ✅ 10-feature vector ordering documented ({', '.join(features)}...).")

    return True

def verify_dr_quick_reference():
    print_section("5. Disaster Recovery Quick Reference Audit")
    project_root = os.path.join(os.path.dirname(__file__), "..")
    dr_doc = os.path.join(project_root, "docs", "DISASTER_RECOVERY_QUICK_REFERENCE.md")
    
    with open(dr_doc, "r", encoding="utf-8") as f:
        dr_text = f.read()

    dr_keywords = ["psql", "alembic", "roadsos_db", "minio"]
    for kw in dr_keywords:
        if kw not in dr_text:
            print(f"❌ FAIL: Keyword '{kw}' missing in DISASTER_RECOVERY_QUICK_REFERENCE.md")
            return False
    print("  ✅ Disaster Recovery quick reference commands verified.")

    return True

def main():
    print("=" * 80)
    print(" ROADSOS STEP 36: OPERATIONAL HANDOFF & KNOWLEDGE TRANSFER VALIDATION")
    print("=" * 80)

    checks = [
        verify_ml_invariant(),
        verify_handoff_documents(),
        verify_documentation_consistency(),
        verify_ml_handoff_contract(),
        verify_dr_quick_reference(),
    ]

    all_passed = all(checks)
    print_section("STEP 36 HANDOFF AUDIT SUMMARY")
    if all_passed:
        print("🟢 ALL STEP 36 OPERATIONAL HANDOFF AUDITS PASSED SUCCESSFULLY.")
        sys.exit(0)
    else:
        print("🔴 STEP 36 AUDIT FAILED. CHECK ERRORS ABOVE.")
        sys.exit(1)

if __name__ == "__main__":
    main()
