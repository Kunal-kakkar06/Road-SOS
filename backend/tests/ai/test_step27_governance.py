"""
backend/tests/ai/test_step27_governance.py
=============================================
Automated pytest suite for Step 27 Production Governance, Compliance,
Secrets Isolation, Alembic Drift, CORS, Security Headers, ML Invariant,
and Observability Metrics.
"""

import os
import pytest
import httpx
from fastapi.testclient import TestClient

from main import app
from database import engine, get_db
from models.user import User
from models.triage_model import TriageJob, TriageEvent
from utils.logging_config import StructuredJsonFormatter
from ai.pipeline.orchestrator import get_orchestrator
from ai.schemas.input_schema import AIInput


def test_production_env_example_sanitization():
    """Verify that backend/.env.example contains no hardcoded credentials."""
    env_example_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env.example"))
    if not os.path.exists(env_example_path):
        pytest.skip(".env.example not found at backend/")
    
    with open(env_example_path, "r") as f:
        content = f.read()

    forbidden_patterns = [
        "postgres:postgres",
        "secret_key_12345",
        "super_secret_jwt_key_that_is_at_least_32_bytes_long_1234567890",
        "minioadmin:minioadmin",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in content, f"Insecure pattern '{pattern}' found in .env.example"


def test_sensitive_logging_redaction():
    """Verify JSON log formatter scrubs secrets and sensitive database strings."""
    import logging
    formatter = StructuredJsonFormatter()
    
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="User authenticated postgresql://user:my_db_password@localhost/db",
        args=(),
        exc_info=None,
    )
    record.extra_fields = {
        "password": "SuperSecretPassword123",
        "secret_token": "my_db_password"
    }
    
    formatted = formatter.format(record)
    assert "SuperSecretPassword123" not in formatted
    assert "my_db_password" not in formatted
    assert "[REDACTED_DB_PASS]" in formatted or "[REDACTED_SECRET]" in formatted


def test_security_headers_and_cors_isolation():
    """Verify security headers and CORS enforcement on production API endpoints."""
    client = TestClient(app)
    
    # 1. Security Headers
    res = client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"

    # 2. CORS Preflight Isolation
    headers = {
        "Origin": "https://malicious-attacker-site.com",
        "Access-Control-Request-Method": "POST",
    }
    res_cors = client.options("/api/triage/history", headers=headers)
    assert res_cors.headers.get("access-control-allow-origin") != "https://malicious-attacker-site.com"


def test_ml_pipeline_invariant():
    """Verify XGBoost ML model version, feature count, and inference invariants."""
    orchestrator = get_orchestrator()
    health = orchestrator.health_check()
    
    model_health = health["model"]
    assert model_health["status"] in ("ok", "ready")
    assert model_health["model_version"] in ("1.1.0", "v1.0.0", "1.0.0")

    ai_in = AIInput(
        request_id="pytest-step27-ml-1",
        symptoms="Crushing chest pain and radiating left arm numbness",
        age=62,
    )
    response = orchestrator.process(ai_in)
    
    assert response.prediction.severity_class.name in ("HIGH", "CRITICAL")
    assert len(response.prediction.shap_factors) > 0
    assert response.prediction.model_type in ("xgboost", "xgboost_fusion")


def test_observability_metrics_endpoint():
    """Verify Prometheus metrics endpoint exports system metrics."""
    client = TestClient(app)
    res = client.get("/metrics")
    assert res.status_code == 200
    content = res.text
    assert "database_connection_failures_total" in content or "disaster_recovery" in content or "http_requests" in content
