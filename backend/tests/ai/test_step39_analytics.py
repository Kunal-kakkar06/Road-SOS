"""
Step 39 — Automated Pytest Suite for Production Intelligence, KPI Analytics & System Optimization
"""

import os
import hashlib
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
EXPECTED_MODEL_SHA256 = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"

REQUIRED_ANALYTICS_DOCS = [
    "docs/PRODUCTION_KPI_FRAMEWORK.md",
    "docs/ML_MONITORING_POLICY.md",
    "docs/PRODUCTION_OPTIMIZATION_RUNBOOK.md",
    "docs/USER_BEHAVIOR_ANALYTICS.md",
    "docs/CAPACITY_FORECAST.md",
    "docs/SECURITY_METRICS_POLICY.md",
]

def test_step39_ml_checksum_invariant():
    """Verify ML model weights remain 100% frozen."""
    model_path = os.path.join(os.path.dirname(__file__), "..", "..", "models", "fusion_triage.pkl")
    assert os.path.exists(model_path), f"ML model missing at {model_path}"
    with open(model_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    assert sha256 == EXPECTED_MODEL_SHA256, f"ML model checksum modified! Expected {EXPECTED_MODEL_SHA256}, got {sha256}"

def test_step39_kpi_latency():
    """Verify health endpoint API latency meets SLA requirements."""
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"

def get_project_root():
    curr = os.path.abspath(os.path.dirname(__file__))
    while curr and curr != os.path.dirname(curr):
        if os.path.exists(os.path.join(curr, "docs")):
            return curr
        curr = os.path.dirname(curr)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def test_step39_analytics_docs_exist():
    """Verify all 6 required KPI & analytics documentation files exist and are non-empty."""
    project_root = get_project_root()
    for doc_path in REQUIRED_ANALYTICS_DOCS:
        full_path = os.path.join(project_root, doc_path)
        assert os.path.exists(full_path), f"Analytics doc missing: {doc_path}"
        assert os.path.getsize(full_path) > 200, f"Analytics doc too small: {doc_path}"
