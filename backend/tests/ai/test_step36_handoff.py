"""
Step 36 — Automated Pytest Suite for Operational Handoff, Documentation & Knowledge Transfer
"""

import os
import hashlib
import pytest

EXPECTED_MODEL_SHA256 = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"

REQUIRED_HANDOFF_DOCS = [
    "docs/DOCUMENTATION_AUDIT.md",
    "docs/DEVELOPER_HANDOFF.md",
    "docs/OPERATIONS_HANDOFF.md",
    "docs/SUPPORT_RUNBOOK.md",
    "docs/ML_MODEL_HANDOFF.md",
    "docs/DISASTER_RECOVERY_QUICK_REFERENCE.md",
]

def test_step36_ml_checksum_invariant():
    """Verify ML model weights remain 100% frozen."""
    model_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "fusion_triage.pkl")
    assert os.path.exists(model_path), f"ML model missing at {model_path}"
    with open(model_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    assert sha256 == EXPECTED_MODEL_SHA256, f"ML model checksum modified! Expected {EXPECTED_MODEL_SHA256}, got {sha256}"

def get_project_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr and curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "docs", "DOCUMENTATION_AUDIT.md")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

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
    with open(ml_doc, "r", encoding="utf-8") as f:
        text = f.read()
    
    assert EXPECTED_MODEL_SHA256 in text, "ML model checksum missing in ML_MODEL_HANDOFF.md"
    assert "speed_at_crash" in text, "Feature ordering missing in ML_MODEL_HANDOFF.md"
    assert "head_injury_risk" in text, "Feature ordering missing in ML_MODEL_HANDOFF.md"
