"""
Step 37 — Automated Pytest Suite for Production Governance, Compliance Evidence & Final Release Audit
"""

import os
import hashlib
import pytest

EXPECTED_MODEL_SHA256 = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"

REQUIRED_GOVERNANCE_DOCS = [
    "docs/DATA_GOVERNANCE_AUDIT.md",
    "docs/AUDIT_TRAIL_VERIFICATION.md",
    "docs/RBAC_LEAST_PRIVILEGE_AUDIT.md",
    "docs/SUPPLY_CHAIN_AUDIT.md",
    "docs/PRODUCTION_CONFIGURATION_AUDIT.md",
    "docs/COMPLIANCE_EVIDENCE_MATRIX.md",
    "docs/FINAL_RELEASE_ARTIFACT_AUDIT.md",
    "docs/reports/STEP37_FINAL_GOVERNANCE_REPORT.md",
]

def test_step37_ml_checksum_invariant():
    """Verify ML model weights remain 100% frozen."""
    model_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "fusion_triage.pkl")
    assert os.path.exists(model_path), f"ML model missing at {model_path}"
    with open(model_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    assert sha256 == EXPECTED_MODEL_SHA256, f"ML model checksum modified! Expected {EXPECTED_MODEL_SHA256}, got {sha256}"

def get_project_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr and curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "docs")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_step37_governance_docs_exist():
    """Verify all 8 required governance & compliance documentation files exist and are non-empty."""
    project_root = get_project_root()
    for doc_path in REQUIRED_GOVERNANCE_DOCS:
        full_path = os.path.join(project_root, doc_path)
        assert os.path.exists(full_path), f"Governance doc missing: {doc_path}"
        assert os.path.getsize(full_path) > 200, f"Governance doc too small: {doc_path}"

def test_step37_compliance_evidence_content():
    """Verify COMPLIANCE_EVIDENCE_MATRIX.md contains required control family evidence."""
    project_root = get_project_root()
    matrix_doc = os.path.join(project_root, "docs", "COMPLIANCE_EVIDENCE_MATRIX.md")
    with open(matrix_doc, "r", encoding="utf-8") as f:
        text = f.read()
    
    assert "Access Control" in text, "Missing Access Control in COMPLIANCE_EVIDENCE_MATRIX.md"
    assert "Disaster Recovery" in text, "Missing Disaster Recovery in COMPLIANCE_EVIDENCE_MATRIX.md"
    assert "ML Governance" in text, "Missing ML Governance in COMPLIANCE_EVIDENCE_MATRIX.md"

def test_step37_lockfile_integrity():
    """Verify requirements.txt and package-lock.json exist for supply chain integrity."""
    project_root = get_project_root()
    assert os.path.exists(os.path.join(project_root, "backend", "requirements.txt")) or os.path.exists(os.path.join(project_root, "requirements.txt")), "requirements.txt missing"
    assert os.path.exists(os.path.join(project_root, "frontend", "package-lock.json")), "package-lock.json missing"
