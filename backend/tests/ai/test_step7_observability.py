import pytest
from fastapi.testclient import TestClient
from main import app
from dependencies.auth_deps import require_user
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from sqlalchemy import select
from models.triage_model import TriageEvent
import asyncio
import time

client = TestClient(app)

@pytest.fixture
def override_user():
    def _override():
        return type("User", (), {"uuid": "test-obs-user", "role": "USER"})()
    app.dependency_overrides[require_user] = _override
    yield
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_request_id_and_sync_metadata(override_user):
    # Clear existing
    async with AsyncSessionLocal() as db:
        await db.execute(TriageEvent.__table__.delete().where(TriageEvent.user_id == "test-obs-user"))
        await db.commit()
        
    payload = {"text": "sync metadata test", "age": 30}
    resp = client.post("/api/triage", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "request_id" in data
    req_id = data["request_id"]
    
    # Check DB directly
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(TriageEvent).where(TriageEvent.id == req_id))
        event = result.scalars().first()
        
        assert event is not None
        assert event.processing_mode == "sync"
        assert event.status == "completed"
        assert event.processing_duration_ms is not None
        assert event.processing_duration_ms >= 0
        assert event.model_version is not None
        assert event.feature_version is not None
        assert event.model_type is not None

@pytest.mark.asyncio
async def test_async_job_metadata(override_user):
    # Clear existing
    async with AsyncSessionLocal() as db:
        await db.execute(TriageEvent.__table__.delete().where(TriageEvent.user_id == "test-obs-user"))
        await db.commit()
        
    payload = {"text": "async metadata test", "age": 30}
    resp = client.post("/api/triage/async", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert "request_id" in data
    
    job_id = data["job_id"]
    req_id = data["request_id"]
    
    from worker import worker_loop
    worker_task = asyncio.create_task(worker_loop())
    
    # Poll
    for _ in range(30):
        poll_resp = client.get(f"/api/triage/jobs/{job_id}")
        if poll_resp.json()["status"] == "completed":
            break
        await asyncio.sleep(0.5)
        
    worker_task.cancel()
        
    poll_data = poll_resp.json()
    assert poll_data["status"] == "completed"
    assert poll_data.get("request_id") == req_id
    
    # Check DB
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(TriageEvent).where(TriageEvent.id == req_id))
        event = result.scalars().first()
        
        assert event is not None
        assert event.processing_mode == "async"
        assert event.job_id == job_id
        assert event.status == "completed"

@pytest.mark.asyncio
async def test_failed_job_persists(override_user):
    # Clear existing
    async with AsyncSessionLocal() as db:
        await db.execute(TriageEvent.__table__.delete().where(TriageEvent.user_id == "test-obs-user"))
        await db.commit()
    
    # We can trigger a failure by passing invalid age type that bypasses validation?
    # Or monkeypatch orchestrator
    import ai.pipeline.orchestrator
    original_process = ai.pipeline.orchestrator.AIOrchestrator.process
    
    def mock_process(self, input):
        raise ValueError("Simulated failure for testing")
        
    ai.pipeline.orchestrator.AIOrchestrator.process = mock_process
    
    try:
        payload = {"text": "fail test"}
        resp = client.post("/api/triage", json=payload)
        assert resp.status_code == 200
        req_id = resp.json().get("request_id")
        assert req_id is not None
        
        # Verify db
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(TriageEvent).where(TriageEvent.id == req_id))
            event = result.scalars().first()
            assert event is not None
            assert event.status == "failed"
            assert event.error_message == "Internal processing error"
    finally:
        ai.pipeline.orchestrator.AIOrchestrator.process = original_process
