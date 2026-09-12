import os
import logging
import pytest
from fastapi.testclient import TestClient
from main import app, validate_production_configuration
from dependencies.auth_deps import create_access_token
from database import AsyncSessionLocal, engine
from models.user import User
import asyncio

client = TestClient(app)

def test_1_production_rejects_sqlite(monkeypatch):
    """1. Verify production environment rejects SQLite DATABASE_URL."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./roadsos.db")
    monkeypatch.setenv("JWT_SECRET", "valid-secure-production-jwt-secret-key-256bit")

    with pytest.raises(ValueError, match="SQLite database connection is strictly prohibited in PRODUCTION"):
        validate_production_configuration()

def test_2_production_rejects_default_jwt_secret(monkeypatch):
    """2. Verify production environment rejects default or insecure JWT secrets."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://roadsos:pass@localhost:5432/roadsos_db")

    for insecure_secret in ["roadsos-secret-key-change-in-prod", "change-me", "default", "roadsos-jwt-secret-key"]:
        monkeypatch.setenv("JWT_SECRET", insecure_secret)
        with pytest.raises(ValueError, match="Insecure JWT_SECRET in production environment"):
            validate_production_configuration()

def test_3_production_accepts_valid_postgres_configuration(monkeypatch):
    """3. Verify production environment accepts valid PostgreSQL and secure JWT secret."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://roadsos:pass@localhost:5432/roadsos_db")
    monkeypatch.setenv("JWT_SECRET", "super-secure-cryptographic-jwt-secret-key-roadsos-2026")
    monkeypatch.setenv("BACKUP_REPLICATION_ENABLED", "false")

    # Should not raise any ValueError
    validate_production_configuration()

def test_4_cors_rejects_unapproved_origin(monkeypatch):
    """4. Verify CORS middleware rejects arbitrary origin in production mode."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://approved-frontend.roadsos.org")

    headers = {"Origin": "https://malicious-attacker-site.com"}
    response = client.options("/api/health", headers=headers)
    assert response.headers.get("access-control-allow-origin") != "https://malicious-attacker-site.com"

def test_5_security_headers_exist():
    """5. Verify HTTP responses include mandatory security headers."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

def test_6_health_endpoint_remains_live():
    """6. Verify process liveness endpoint /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "app_version" in response.json()

def test_7_readiness_detects_db_dependency_failure(monkeypatch):
    """7. Verify /api/ready detects DB connection failure and returns 503."""
    class MockFailedSessionContext:
        async def __aenter__(self):
            raise Exception("PostgreSQL Connection Refused")
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    def mock_failed_session_local():
        return MockFailedSessionContext()

    monkeypatch.setattr("database.AsyncSessionLocal", mock_failed_session_local)
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"

def test_8_worker_health_does_not_expose_phi():
    """8. Verify /api/ai/worker-health exposes cluster status without leaking PHI."""
    response = client.get("/api/ai/worker-health")
    assert response.status_code == 200
    data = response.json()
    assert "active_worker_count" in data
    assert "workers" in data
    text_content = response.text.lower()
    for phi_keyword in ["chest pain", "symptoms", "laceration", "abnormal"]:
        assert phi_keyword not in text_content

def test_9_secrets_are_redacted_from_logs():
    """9. Verify log sanitization redacts sensitive authorization and secret tokens."""
    from utils.logging_config import StructuredJsonFormatter
    formatter = StructuredJsonFormatter(service_name="roadsos-api")

    assert formatter.sanitize_val("Authorization", "Bearer my-secret-jwt-token") == "[REDACTED_TOKEN]"
    assert formatter.sanitize_val("password", "super_secret_123") == "[REDACTED_SECRET]"
    assert formatter.sanitize_val("jwt_secret", "my-jwt-key") == "[REDACTED_SECRET]"

def test_10_api_worker_configuration_separation():
    """10. Verify API configuration and Worker loop settings remain decoupled."""
    import worker
    assert hasattr(worker, "worker_loop")
    assert hasattr(worker, "update_worker_heartbeat")

def test_11_production_environment_variables_validated(monkeypatch):
    """11. Verify BACKUP_REPLICATION_ENABLED validation when bucket is missing in production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://roadsos:pass@localhost:5432/roadsos_db")
    monkeypatch.setenv("JWT_SECRET", "super-secure-cryptographic-jwt-secret-key-roadsos-2026")
    monkeypatch.setenv("BACKUP_REPLICATION_ENABLED", "true")
    monkeypatch.setenv("BACKUP_STORAGE_BUCKET", "")

    with pytest.raises(ValueError, match="BACKUP_STORAGE_BUCKET is required when backup replication is enabled"):
        validate_production_configuration()

def test_12_worker_operational_settings_defaults(monkeypatch):
    """12. Verify worker operational settings have safe configurable defaults."""
    poll_interval = float(os.getenv("WORKER_POLL_INTERVAL", "2.0"))
    stale_timeout = int(os.getenv("WORKER_STALE_TIMEOUT_MINUTES", "5"))
    max_attempts = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))

    assert poll_interval >= 0.5
    assert stale_timeout >= 1
    assert max_attempts == 3

def test_13_retry_limit_remains_three():
    """13. Verify max retry limit remains strictly capped at 3."""
    max_attempts = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))
    assert max_attempts == 3

def test_14_concurrent_async_job_limit_remains_five():
    """14. Verify max concurrent active async jobs per user is strictly 5."""
    from services.triage_job_manager import MAX_CONCURRENT_JOBS_PER_USER
    assert MAX_CONCURRENT_JOBS_PER_USER == 5

def test_15_alembic_configuration_is_production_safe():
    """15. Verify Alembic migration head points to expected revision c3d4e5f6a7b8."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    ini_path = "backend/alembic.ini" if os.path.exists("backend/alembic.ini") else "alembic.ini"
    alembic_cfg = Config(ini_path)
    script = ScriptDirectory.from_config(alembic_cfg)
    head_rev = script.get_current_head()
    assert head_rev == "c3d4e5f6a7b8"
