"""
Step 40 — Automated Pytest Suite for Final Production Release Certification & Handover
"""

import os
import hashlib
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
EXPECTED_MODEL_SHA256 = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"

REQUIRED_STEP40_DOCS = [
    "docs/FINAL_PRODUCTION_CERTIFICATION.md",
    "docs/SYSTEM_HANDOVER_MANIFEST.md",
    "docs/ROADSOS_V1_PRODUCTION_RELEASE_NOTES.md",
]

def test_step40_ml_checksum_invariant():
    """Verify ML model weights remain 100% frozen."""
    model_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "fusion_triage.pkl")
    assert os.path.exists(model_path), f"ML model missing at {model_path}"
    with open(model_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    assert sha256 == EXPECTED_MODEL_SHA256, f"ML model checksum modified! Expected {EXPECTED_MODEL_SHA256}, got {sha256}"

def test_step40_api_health():
    """Verify API health endpoint returns status ok."""
    res = client.get("/health")
    assert res.status_code == 200, f"Health endpoint returned {res.status_code}"
    assert res.json().get("status") in ["ok", "healthy"], "Health check status not ok"

def get_project_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr and curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "docs")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_step40_final_docs_exist():
    """Verify all Step 40 final production release documents exist and are non-empty."""
    project_root = get_project_root()
    for doc_path in REQUIRED_STEP40_DOCS:
        full_path = os.path.join(project_root, doc_path)
        assert os.path.exists(full_path), f"Step 40 doc missing: {doc_path}"
        assert os.path.getsize(full_path) > 200, f"Step 40 doc too small: {doc_path}"
