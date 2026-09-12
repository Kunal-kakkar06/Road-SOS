import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app
from dependencies.auth_deps import require_user
from routers.triage import TriageRequest

@pytest.fixture(autouse=True)
def override_user_fixture():
    app.dependency_overrides[require_user] = lambda: type("User", (), {"uuid": "test-user-123", "role": "USER"})()
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

@pytest.mark.asyncio
async def test_async_triage_lifecycle():
    # 1. Submission
    payload = {"text": "Patient has severe chest pain", "age": 45}
    resp = client.post("/api/triage/async", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    
    job_id = data["job_id"]
    
    from worker import worker_loop
    worker_task = asyncio.create_task(worker_loop())
    
    # 2. Polling loop
    max_attempts = 30
    for _ in range(max_attempts):
        status_resp = client.get(f"/api/triage/jobs/{job_id}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        
        if status_data["status"] == "completed":
            assert "result" in status_data
            result = status_data["result"]
            assert "severity_score" in result
            assert result["severity_level"] in ["Critical", "High", "Moderate", "Low"]
            break
        elif status_data["status"] == "failed":
            worker_task.cancel()
            pytest.fail(f"Job failed: {status_data.get('error')}")
            
        import time
        await asyncio.sleep(0.5)
    else:
        worker_task.cancel()
        pytest.fail("Async triage did not complete within timeout")
        
    worker_task.cancel()

def test_unauthorized_job_access():
    payload = {"text": "Minor headache", "age": 30}
    resp = client.post("/api/triage/async", json=payload)
    job_id = resp.json()["job_id"]
    
    # Switch user
    app.dependency_overrides[require_user] = lambda: type("User", (), {"uuid": "test-user-456", "role": "USER"})()
    
    status_resp = client.get(f"/api/triage/jobs/{job_id}")
    assert status_resp.status_code == 404

    # Restore user
    app.dependency_overrides[require_user] = lambda: type("User", (), {"uuid": "test-user-123", "role": "USER"})()

def test_sync_triage_compatibility():
    payload = {"text": "Broken leg"}
    resp = client.post("/api/triage", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "severity_level" in data
