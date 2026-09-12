import os
import uuid
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from database import engine
from main import app
from dependencies.auth_deps import require_user

class MockUser:
    uuid = "test-step17-user-uuid"
    role = "USER"

@pytest.fixture
def client():
    app.dependency_overrides[require_user] = lambda: MockUser()
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_connection_pool_environment_variables(monkeypatch):
    monkeypatch.setenv("DB_POOL_SIZE", "25")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "15")
    monkeypatch.setenv("DB_POOL_TIMEOUT", "45.0")
    
    assert int(os.getenv("DB_POOL_SIZE")) == 25
    assert int(os.getenv("DB_MAX_OVERFLOW")) == 15
    assert float(os.getenv("DB_POOL_TIMEOUT")) == 45.0

def test_api_health_endpoints(client):
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"
    assert res_health.json()["liveness"] is True

    res_ready = client.get("/api/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"

    res_ai = client.get("/api/ai/health")
    assert res_ai.status_code == 200
    assert res_ai.json()["status"] in ["ok", "healthy"]

def test_api_metrics_endpoint_visibility(client):
    res_metrics = client.get("/api/metrics")
    assert res_metrics.status_code == 200
    data = res_metrics.json()
    assert "triage_jobs" in data
    assert "workers" in data
    assert "pending" in data["triage_jobs"]
    assert "completed" in data["triage_jobs"]
    assert "active" in data["workers"]
    assert "stale" in data["workers"]

def test_security_headers_active(client):
    res = client.get("/api/health")
    assert res.headers.get("X-Content-Type-Options") == "nosniff"
    assert res.headers.get("X-Frame-Options") == "DENY"

def test_unauthenticated_request_blocked():
    app.dependency_overrides.clear()
    unauth_client = TestClient(app)
    res = unauth_client.post("/api/triage", json={"text": "chest pain"})
    assert res.status_code == 401

def test_invalid_input_payload_boundaries(client):
    # Authenticated user sending invalid latitude (>90.0) -> 422
    res = client.post("/api/triage", json={"latitude": 199.0})
    assert res.status_code == 422

@pytest.mark.asyncio
async def test_idempotent_triage_event_creation():
    from database import AsyncSessionLocal
    from routers.triage import _execute_triage_pipeline, TriageRequest
    from models.triage_model import TriageEvent
    from sqlalchemy import select

    req = TriageRequest(text="Severe chest pain and difficulty breathing", age=45, gender="male")
    request_id = f"test-step17-idempotent-{uuid.uuid4()}"

    async with AsyncSessionLocal() as db:
        # First execution
        res1 = await _execute_triage_pipeline(req, db, user_id="user-123", processing_mode="sync", request_id=request_id)
        assert res1["request_id"] == request_id

        # Second execution with same request_id (simulating retry)
        res2 = await _execute_triage_pipeline(req, db, user_id="user-123", processing_mode="sync", request_id=request_id)
        assert res2["request_id"] == request_id

        # Query database to confirm exactly 1 TriageEvent row exists
        stmt = select(TriageEvent).where(TriageEvent.event_id == request_id)
        db_res = await db.execute(stmt)
        events = db_res.scalars().all()
        assert len(events) == 1
        assert events[0].status == "completed"

@pytest.mark.asyncio
async def test_worker_heartbeat_updates():
    from database import AsyncSessionLocal
    from worker import update_worker_heartbeat
    from models.worker_model import WorkerHeartbeat
    from sqlalchemy import select

    worker_id = f"test-worker-step17-{uuid.uuid4()}"
    async with AsyncSessionLocal() as db:
        # Register heartbeat
        await update_worker_heartbeat(db, worker_id, status="active", current_job_id="job-1")

        stmt = select(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == worker_id)
        res = await db.execute(stmt)
        record = res.scalars().first()
        assert record is not None
        assert record.status == "active"
        assert record.current_job_id == "job-1"

        # Update heartbeat with completed job
        await update_worker_heartbeat(db, worker_id, status="active", current_job_id=None, inc_completed=True)
        res2 = await db.execute(stmt)
        record2 = res2.scalars().first()
        assert record2.completed_jobs == 1
        assert record2.current_job_id is None

def test_backup_script_import_and_masking():
    from scripts.backup_db import mask_url
    url = "postgresql://roadsos:secretpass123@localhost:5432/roadsos_db"
    masked = mask_url(url)
    assert "secretpass123" not in masked
    assert "****" in masked
