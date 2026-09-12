import pytest
from httpx import AsyncClient
import time
import uuid
import ai.pipeline.orchestrator
from fastapi.testclient import TestClient
from main import app
from dependencies.auth_deps import create_access_token

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers_user_a():
    token = create_access_token("user-a-uuid", "USER")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_user_b():
    token = create_access_token("user-b-uuid", "USER")
    return {"Authorization": f"Bearer {token}"}

from database import AsyncSessionLocal

@pytest.fixture(autouse=True)
def cleanup_jobs():
    import asyncio
    from models.triage_model import TriageJob
    from sqlalchemy import delete
    
    async def _clean():
        async with AsyncSessionLocal() as db:
            await db.execute(delete(TriageJob))
            await db.commit()
            
    asyncio.run(_clean())

@pytest.mark.asyncio
async def test_job_survives_restart_simulation(client, auth_headers_user_a):
    # We will simulate a restart by calling create_job directly, which puts it in DB,
    # then we'll fetch it using the API. Because it's DB-backed, it works without
    # an in-memory dictionary.
    from services.triage_job_manager import create_job
    
    # 1. Create job using manager
    async with AsyncSessionLocal() as db:
        job_id = await create_job("user-a-uuid", db, "test-req", {})
    
    # 2. Fetch using API
    resp = client.get(f"/api/triage/jobs/{job_id}", headers=auth_headers_user_a)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

@pytest.mark.asyncio
async def test_job_idor_protection(client, auth_headers_user_a, auth_headers_user_b):
    from services.triage_job_manager import create_job
    
    # User A creates job
    async with AsyncSessionLocal() as db:
        job_id = await create_job("user-a-uuid", db, "test-req", {})
    
    # User B tries to fetch it
    resp = client.get(f"/api/triage/jobs/{job_id}", headers=auth_headers_user_b)
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_rate_limiting_works_with_db(client, auth_headers_user_a):
    from services.triage_job_manager import create_job
    
    # Create 5 pending jobs
    async with AsyncSessionLocal() as db:
        for _ in range(5):
            await create_job("user-a-uuid", db, "test-req", {})
        
    # Attempt 6th
    resp = client.post("/api/triage/async", json={"text": "Should fail"}, headers=auth_headers_user_a)
    assert resp.status_code == 429
    assert "Too many concurrent triage requests" in resp.json()["detail"]

@pytest.mark.asyncio
async def test_job_completed_lifecycle(client, auth_headers_user_a):
    import asyncio
    from worker import worker_loop
    
    resp = client.post("/api/triage/async", json={"text": "I have a headache"}, headers=auth_headers_user_a)
    assert resp.status_code == 202
    
    job_id = resp.json()["job_id"]
    
    # Start worker to process it
    worker_task = asyncio.create_task(worker_loop())
    await asyncio.sleep(2)
    worker_task.cancel()
    
    resp2 = client.get(f"/api/triage/jobs/{job_id}", headers=auth_headers_user_a)
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["status"] == "completed"
    assert "result" in data
    assert data["result"]["severity_level"] == "Moderate"
