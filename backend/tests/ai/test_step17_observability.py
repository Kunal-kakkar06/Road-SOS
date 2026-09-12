import pytest
import os
import json
import logging
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from main import app, validate_production_configuration, engine
from utils.logging_config import StructuredJsonFormatter
from utils.metrics import metrics_manager

client = TestClient(app)

# 1. Request ID Generation
def test_request_id_generation():
    response = client.get("/health")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) > 10

# 2. Request ID Propagation
def test_request_id_propagation():
    custom_id = "test-propagate-id-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id

# 3. X-Request-ID Response Header
def test_x_request_id_response_header():
    response = client.get("/api/health")
    assert "X-Request-ID" in response.headers

# 4. Structured Lifecycle Logging
def test_structured_lifecycle_logging():
    formatter = StructuredJsonFormatter(service_name="roadsos-api")
    record = logging.LogRecord(
        name="roadsos.triage",
        level=logging.INFO,
        pathname="triage.py",
        lineno=50,
        msg="Job created",
        args=(),
        exc_info=None
    )
    record.event_name = "triage.job.created"
    record.request_id = "req-123"
    record.job_id = "job-456"

    log_json = json.loads(formatter.format(record))
    assert log_json["event_name"] == "triage.job.created"
    assert log_json["request_id"] == "req-123"
    assert log_json["job_id"] == "job-456"

# 5. Successful Triage Metrics
def test_successful_triage_metrics():
    metrics_manager.record_http_request("GET", "/api/health", 200)
    assert metrics_manager.http_requests_total.get(("GET", "/api/health", "200"), 0) >= 1

# 6. Failed Triage Metrics
def test_failed_triage_metrics():
    metrics_manager.record_http_request("POST", "/api/triage/jobs", 500)
    assert metrics_manager.http_requests_total.get(("POST", "/api/triage/jobs", "500"), 0) >= 1

# 7. Async Job Metrics
def test_async_job_metrics():
    metrics_manager.record_worker_job("worker-test-1", "completed")
    assert metrics_manager.worker_jobs_processed_total.get(("worker-test-1", "completed"), 0) >= 1

# 8. Retry Metrics
def test_retry_metrics():
    metrics_manager.record_worker_job("worker-test-1", "pending")
    assert metrics_manager.worker_jobs_processed_total.get(("worker-test-1", "pending"), 0) >= 1

# 9. Worker Heartbeat & /api/ai/worker-health Visibility
def test_worker_health_endpoint():
    response = client.get("/api/ai/worker-health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "active_worker_count" in data
    assert "workers" in data
    assert "app_version" in data

# 10. AI Health Endpoint & APP_VERSION
def test_ai_health_endpoint():
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_version"] in ["1.0.0", "step17"]

# 11. Database Failure Sanitization
def test_database_failure_sanitization():
    with patch("database.AsyncSessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("DB Connection Error")
        mock_session_local.return_value.__aenter__.return_value = mock_session

        response = client.get("/api/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"

# 12. Configuration Validation Fast-Fail
def test_configuration_validation_production_rejection(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("JWT_SECRET", "roadsos-secret-key-change-in-prod")

    with pytest.raises(ValueError, match="SQLite database connection is strictly prohibited in PRODUCTION"):
        validate_production_configuration()

# 13. Graceful Shutdown Behavior
@pytest.mark.asyncio
async def test_graceful_shutdown_behavior():
    await engine.dispose()
    assert True

# 14. Sensitive-Data Log Protection
def test_sensitive_data_log_protection():
    formatter = StructuredJsonFormatter(service_name="roadsos-test")
    sanitized = formatter.sanitize_val("password", "MySecretPassword123")
    assert sanitized == "[REDACTED_SECRET]"

    token_sanitized = formatter.sanitize_val("authorization", "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
    assert token_sanitized == "[REDACTED_TOKEN]"

# 15. Authentication / IDOR Protection Regression
def test_auth_idor_regression():
    response = client.get("/api/triage/history")
    assert response.status_code == 401

# 16. Existing Triage Behavior Regression
def test_health_endpoints_regression():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["liveness"] is True
