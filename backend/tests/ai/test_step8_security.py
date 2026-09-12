import pytest
from fastapi.testclient import TestClient
from main import app
from dependencies.auth_deps import create_access_token, require_user
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from models.user import User
from models.triage_model import TriageEvent
import uuid

client = TestClient(app)

@pytest.fixture
def auth_headers_user_a():
    token = create_access_token("user-a-uuid", "USER")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_user_b():
    token = create_access_token("user-b-uuid", "USER")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def setup_users():
    import asyncio
        
    async def _setup():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import delete
            await db.execute(delete(User).where(User.email.in_(["usera@example.com", "userb@example.com"])))
            await db.commit()
            
            for u in [
                User(uuid="user-a-uuid", email="usera@example.com", is_active=True, role="USER", hashed_password="hash", name="User A"),
                User(uuid="user-b-uuid", email="userb@example.com", is_active=True, role="USER", hashed_password="hash", name="User B")
            ]:
                db.add(u)
            await db.commit()
            
    asyncio.run(_setup())
    yield

def test_unauthorized_rejected():
    resp = client.post("/api/triage", json={"text": "help"})
    assert resp.status_code == 401
    assert "Not authenticated" in resp.json()["detail"]

def test_invalid_jwt_rejected():
    resp = client.post("/api/triage", json={"text": "help"}, headers={"Authorization": "Bearer fake.jwt.token"})
    assert resp.status_code == 401

def test_idor_job_isolation(setup_users, auth_headers_user_a, auth_headers_user_b):
    # User A creates a job
    resp = client.post("/api/triage/async", json={"text": "user a text"}, headers=auth_headers_user_a)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    
    # User B tries to fetch User A's job
    resp_b = client.get(f"/api/triage/jobs/{job_id}", headers=auth_headers_user_b)
    assert resp_b.status_code == 404
    assert resp_b.json()["detail"] == "Job not found"

def test_input_validation(setup_users, auth_headers_user_a):
    # Invalid latitude
    resp = client.post("/api/triage", json={"text": "help", "latitude": 900.0}, headers=auth_headers_user_a)
    assert resp.status_code == 422
    
    # Text too long
    long_text = "a" * 2500
    resp = client.post("/api/triage", json={"text": long_text}, headers=auth_headers_user_a)
    assert resp.status_code == 422

@pytest.mark.asyncio
async def test_async_job_rate_limit(setup_users, auth_headers_user_a):
    from services.triage_job_manager import create_job
    from database import AsyncSessionLocal
    from models.triage_model import TriageJob
    from sqlalchemy import delete
    
    # Manually insert 5 pending jobs
    async with AsyncSessionLocal() as db:
        await db.execute(delete(TriageJob))
        for _ in range(5):
            await create_job("user-a-uuid", db, "test-req-id", {})
            
    try:
        # The 6th should be rejected with 429
        resp = client.post("/api/triage/async", json={"text": "job 6"}, headers=auth_headers_user_a)
        assert resp.status_code == 429
        assert "Too many concurrent triage requests" in resp.json()["detail"]
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(TriageJob))
            await db.commit()

def test_global_exception_handler(setup_users, auth_headers_user_a):
    # We can trigger an unhandled exception by monkeypatching the orchestrator
    import ai.pipeline.orchestrator
    original_process = ai.pipeline.orchestrator.AIOrchestrator.process
    
    def mock_process(self, input):
        raise RuntimeError("Simulated explosive failure")
        
    ai.pipeline.orchestrator.AIOrchestrator.process = mock_process
    
    try:
        # Triage actually handles exceptions internally in _execute_triage_pipeline to persist a failed TriageEvent.
        # Wait, if _execute_triage_pipeline handles it and returns 200 with fallback, the global exception handler isn't hit!
        # That's actually correct and secure! Let's verify it doesn't leak stack traces.
        resp = client.post("/api/triage", json={"text": "trigger error"}, headers=auth_headers_user_a)
        
        # In Step 7 we implemented fallback logging that returns 200 with default mock assessment if inference fails.
        # So we should expect 200, and no stack trace in the client.
        assert resp.status_code == 200
        assert "Simulated explosive failure" not in resp.text
        assert "Traceback" not in resp.text
    finally:
        ai.pipeline.orchestrator.AIOrchestrator.process = original_process

    # To actually hit the 500 handler, let's hit a non-existent endpoint or force a crash in a dependency
    # We must use raise_server_exceptions=False to see the 500 response in TestClient
    client_no_exc = TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides[require_user] = lambda: (_ for _ in ()).throw(RuntimeError("Deps crash"))
    resp = client_no_exc.get("/api/triage/history")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "An unexpected internal error occurred."
    app.dependency_overrides.clear()
