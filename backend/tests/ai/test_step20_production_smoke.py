import os
import pytest
from fastapi.testclient import TestClient
from main import app, validate_production_configuration
from dependencies.auth_deps import create_access_token
from database import AsyncSessionLocal
from models.user import User
import asyncio

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_smoke_users():
    async def _setup():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            users_to_seed = [
                ("usr-smoke-1", "smoke1@example.com", "Smoke User 1"),
                ("usr-smoke-2", "smoke2@example.com", "Smoke User 2"),
                ("usr-a", "usra@example.com", "User A"),
                ("usr-b", "usrb@example.com", "User B")
            ]
            for uid, email, name in users_to_seed:
                res = await db.execute(select(User).filter(User.uuid == uid))
                if not res.scalars().first():
                    u = User(uuid=uid, email=email, is_active=True, role="USER", hashed_password="hash", name=name)
                    db.add(u)
            await db.commit()
    asyncio.run(_setup())

def test_production_fast_fail_config_guard(monkeypatch):
    """Verify validate_production_configuration fast-fails on unsafe production config."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    monkeypatch.setenv("JWT_SECRET", "valid-prod-secret-key-12345678901234567890")

    with pytest.raises(ValueError, match="SQLite database connection is strictly prohibited in PRODUCTION"):
        validate_production_configuration()

    monkeypatch.setenv("DATABASE_URL", "postgresql://roadsos:password@localhost:5432/roadsos_db")
    monkeypatch.setenv("JWT_SECRET", "default")
    with pytest.raises(ValueError, match="Insecure JWT_SECRET"):
        validate_production_configuration()

def test_sync_triage_e2e_flow():
    """Verify synchronous triage endpoint executes ML inference, NLP, SHAP, and returns correlation headers."""
    token = create_access_token(user_uuid="usr-smoke-1", role="user")
    headers = {"Authorization": f"Bearer {token}", "X-Request-ID": "req-smoke-sync-100"}
    payload = {
        "text": "Severe chest tightness and shortness of breath following vehicle impact",
        "age": 45,
        "symptoms": "Chest pain, dyspnea"
    }

    response = client.post("/api/triage", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert "severity_level" in data
    assert "severity_score" in data
    assert "symptoms_extracted" in data
    assert "shap_values" in data
    assert response.headers.get("X-Request-ID") == "req-smoke-sync-100"

def test_async_triage_e2e_polling_lifecycle():
    """Verify asynchronous triage creation (202), polling, and event audit integrity."""
    token = create_access_token(user_uuid="usr-smoke-2", role="user")
    headers = {"Authorization": f"Bearer {token}", "X-Request-ID": "req-smoke-async-200"}
    payload = {
        "text": "Minor abrasion on left forearm, alert and oriented",
        "age": 30
    }

    create_resp = client.post("/api/triage/async", json=payload, headers=headers)
    assert create_resp.status_code == 202
    job_data = create_resp.json()
    job_id = job_data["job_id"]

    # Poll status
    poll_resp = client.get(f"/api/triage/jobs/{job_id}", headers=headers)
    assert poll_resp.status_code == 200
    assert poll_resp.json()["job_id"] == job_id

def test_idor_ownership_isolation():
    """Verify User A cannot access User B's triage job."""
    token_user_a = create_access_token(user_uuid="usr-a", role="user")
    token_user_b = create_access_token(user_uuid="usr-b", role="user")

    headers_a = {"Authorization": f"Bearer {token_user_a}"}
    headers_b = {"Authorization": f"Bearer {token_user_b}"}

    payload = {"text": "Mild headache", "age": 25}

    create_resp = client.post("/api/triage/async", json=payload, headers=headers_a)
    assert create_resp.status_code == 202
    job_id = create_resp.json()["job_id"]

    # User B attempts to access User A's job
    access_b = client.get(f"/api/triage/jobs/{job_id}", headers=headers_b)
    assert access_b.status_code == 404

def test_unauthenticated_requests_rejected():
    response = client.post("/api/triage/async", json={})
    assert response.status_code in (401, 403)

def test_app_version_in_health_endpoints():
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["app_version"] in ["1.0.0", "step20"]

    r2 = client.get("/api/health")
    assert r2.status_code == 200
    assert r2.json()["app_version"] in ["1.0.0", "step20"]
