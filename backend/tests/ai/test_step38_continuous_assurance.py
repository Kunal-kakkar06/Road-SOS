"""
Step 38 — Automated Pytest Suite for Continuous Production Assurance, SLO Governance & Preventive Maintenance
"""

import os
import hashlib
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
EXPECTED_MODEL_SHA256 = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"

REQUIRED_ASSURANCE_DOCS = [
    "docs/DEPENDENCY_MAINTENANCE_POLICY.md",
    "docs/CONTAINER_PATCHING_RUNBOOK.md",
    "docs/SECRET_ROTATION_RUNBOOK.md",
    "docs/DATABASE_MAINTENANCE_RUNBOOK.md",
    "docs/ERROR_BUDGET_POLICY.md",
    "docs/INCIDENT_POSTMORTEM_TEMPLATE.md",
    "docs/PRODUCTION_INCIDENT_LOG.md",
]

def test_step38_ml_checksum_invariant():
    """Verify ML model weights remain 100% frozen."""
    model_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "fusion_triage.pkl")
    assert os.path.exists(model_path), f"ML model missing at {model_path}"
    with open(model_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    assert sha256 == EXPECTED_MODEL_SHA256, f"ML model checksum modified! Expected {EXPECTED_MODEL_SHA256}, got {sha256}"

def test_step38_slo_and_health():
    """Verify /health API endpoint returns 200 OK for SLO availability."""
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed with {res.status_code}"
    assert res.json().get("status") in ["healthy", "ok"], "Health check status not healthy"

def test_step38_security_smoke_suite():
    """Verify invalid and alg=none JWTs are rejected with 401."""
    res_inv = client.get("/api/triage/jobs/job-123", headers={"Authorization": "Bearer bad_token"})
    assert res_inv.status_code == 401, "Invalid JWT should return 401"
    
    res_alg = client.get("/api/triage/jobs/job-123", headers={"Authorization": "Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0."})
    assert res_alg.status_code == 401, "Alg=none JWT should return 401"

def get_project_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr and curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "docs")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_step38_assurance_docs_exist():
    """Verify all 7 required assurance runbooks exist and are non-empty."""
    project_root = get_project_root()
    for doc_path in REQUIRED_ASSURANCE_DOCS:
        full_path = os.path.join(project_root, doc_path)
        assert os.path.exists(full_path), f"Assurance doc missing: {doc_path}"
        assert os.path.getsize(full_path) > 200, f"Assurance doc too small: {doc_path}"
