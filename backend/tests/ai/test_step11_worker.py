import pytest
from httpx import AsyncClient
from sqlalchemy import select
from models.triage_model import TriageJob, TriageEvent
import uuid
import asyncio
from fastapi.testclient import TestClient
from main import app
from dependencies.auth_deps import create_access_token
from database import AsyncSessionLocal

client_test = TestClient(app)

from models.user import User

@pytest.fixture(autouse=True)
def setup_user_a():
    async def _setup():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            res = await db.execute(select(User).where(User.uuid == "user-a-uuid"))
            if not res.scalars().first():
                user_a = User(
                    uuid="user-a-uuid",
                    email="worker_usera@example.com",
                    is_active=True,
                    role="USER",
                    hashed_password="hash",
                    name="User A"
                )
                db.add(user_a)
                await db.commit()
    asyncio.run(_setup())

@pytest.fixture
def client():
    return client_test

@pytest.fixture
def auth_headers_user_a():
    token = create_access_token("user-a-uuid", "USER")
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_worker_processes_pending_job(client, auth_headers_user_a):
    async with AsyncSessionLocal() as db_session:
        payload = {
            "text": "My head hurts and I feel dizzy.",
            "has_image": False,
            "has_sensor_data": False,
            "voice_transcript": ""
        }
        # 1. Submit an async job (which now only creates the DB row)
        resp = client.post("/api/triage/async", json=payload, headers=auth_headers_user_a)
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]
        
        # Verify job is pending
        stmt = select(TriageJob).where(TriageJob.id == job_id)
        res = await db_session.execute(stmt)
        job = res.scalars().first()
        assert job is not None
        assert job.status == "pending"
        assert job.payload["text"] == "My head hurts and I feel dizzy."
        
        # 2. Start a mock worker task to process it
        from worker import worker_loop
        worker_task = asyncio.create_task(worker_loop())
        
        # Give it a second to claim and process
        await asyncio.sleep(2)
        worker_task.cancel()
    
        # 3. Verify job is completed
        await db_session.refresh(job)
        assert job.status == "completed"
        assert job.worker_id is not None
        assert job.result is not None
        
        # 4. Verify TriageEvent was created
        stmt_ev = select(TriageEvent).where(TriageEvent.job_id == job_id)
        res_ev = await db_session.execute(stmt_ev)
        event = res_ev.scalars().first()
        assert event is not None
        assert event.processing_mode == "async"
