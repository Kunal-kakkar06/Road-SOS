import pytest
import json
import logging
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from main import app
from utils.logging_config import StructuredJsonFormatter, setup_structured_logging
from utils.metrics import metrics_manager

client = TestClient(app)

def test_request_correlation_header_propagation():
    """Verify X-Request-ID header is propagated and returned in HTTP responses."""
    custom_id = "test-correlation-id-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id

def test_request_correlation_generation():
    """Verify unique UUID request ID is generated when X-Request-ID is missing."""
    response = client.get("/health")
    assert response.status_code == 200
    generated_id = response.headers.get("X-Request-ID")
    assert generated_id is not None
    assert len(generated_id) > 10

def test_structured_json_formatter():
    """Verify StructuredJsonFormatter outputs valid JSON with required fields."""
    formatter = StructuredJsonFormatter(service_name="roadsos-test")
    record = logging.LogRecord(
        name="roadsos.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test event message",
        args=(),
        exc_info=None
    )
    record.event_name = "test.event.fired"
    record.request_id = "req-uuid-999"

    formatted_str = formatter.format(record)
    data = json.loads(formatted_str)

    assert data["service"] == "roadsos-test"
    assert data["level"] == "INFO"
    assert data["event_name"] == "test.event.fired"
    assert data["request_id"] == "req-uuid-999"
    assert "timestamp" in data

def test_sensitive_data_redaction():
    """Verify log redaction strips passwords, JWT Bearer tokens, DB credentials, and patient text."""
    formatter = StructuredJsonFormatter(service_name="roadsos-test")
    
    # 1. Test JWT Bearer redaction
    assert formatter.sanitize_val("authorization", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9") == "[REDACTED_TOKEN]"
    
    # 2. Test password redaction
    assert formatter.sanitize_val("password", "MySuperSecret123") == "[REDACTED_SECRET]"
    
    # 3. Test DB credential URL redaction
    db_url = "postgresql+asyncpg://admin_user:super_secret_db_pass@localhost:5432/roadsos_db"
    sanitized_db_url = formatter.sanitize_val("database_url", db_url)
    assert "super_secret_db_pass" not in sanitized_db_url
    assert "[REDACTED_DB_PASS]" in sanitized_db_url

    # 4. Test patient symptom text redaction
    assert formatter.sanitize_val("symptoms", "Patient has severe chest pain and breathlessness") == "[REDACTED_SENSITIVE]"

def test_prometheus_metrics_endpoint():
    """Verify /metrics returns Prometheus text format with key system metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    content = response.text

    assert "http_requests_total" in content
    assert "triage_jobs_total" in content
    assert "worker_nodes_active" in content
    assert "disaster_recovery_latest_backup_age_seconds" in content

def test_liveness_health_endpoint():
    """Verify liveness endpoint /api/health returns 200 OK independent of database state."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["liveness"] is True

@pytest.mark.asyncio
async def test_readiness_probe_failure():
    """Verify /api/ready returns 503 Service Unavailable when database connection fails."""
    with patch("database.AsyncSessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("DB Connection Refused")
        mock_session_local.return_value.__aenter__.return_value = mock_session

        response = client.get("/api/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert "checks" in data
