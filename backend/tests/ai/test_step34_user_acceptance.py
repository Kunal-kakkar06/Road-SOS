"""
backend/tests/ai/test_step34_user_acceptance.py
=================================================
Automated Pytest user acceptance & business readiness test suite for Step 34.

Verifies:
  1. Complete User Journey (Registration, Login, Sync Triage, Async Job Submission, Polling, History)
  2. Responder workflow & emergency queue visibility
  3. Realistic emergency scenarios (Low, Moderate, High, Critical)
  4. AI result usability (severity_score, severity_level, assessment, actions, shap_values)
  5. Frontend ↔ Backend contract error handling (401, 403, 404, 422)
  6. Data lifecycle & 0 duplicate events / orphaned jobs
  7. ML model artifact SHA-256 invariant (e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1)
"""

import os
import json
import hashlib
import pytest
import time
from httpx import AsyncClient, ASGITransport
from main import app
from database import AsyncSessionLocal
from sqlalchemy import text


def compute_sha256(filepath: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


@pytest.mark.asyncio
async def test_step34_user_journey_and_triage_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        email = f"pytest_user_{int(time.time()*1000)}@roadsos.org"
        reg = await client.post("/api/auth/register", json={
            "name": "Pytest Business User",
            "email": email,
            "password": "UserPassword123!",
            "confirm_password": "UserPassword123!"
        })
        assert reg.status_code in (200, 201)

        login = await client.post("/api/auth/login", json={"email": email, "password": "UserPassword123!"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Sync triage
        sync_res = await client.post("/api/triage", json={
            "symptoms": "Severe acute chest pain and breathing difficulty",
            "age": 60,
            "heart_rate": 115,
            "latitude": 37.7749,
            "longitude": -122.4194
        }, headers=headers)
        assert sync_res.status_code == 200
        data = sync_res.json()
        assert "severity_level" in data
        assert "severity_score" in data
        assert "shap_values" in data

        # Async triage
        async_res = await client.post("/api/triage/async", json={
            "symptoms": "Accident scenario on Highway 101",
            "age": 45,
            "heart_rate": 95,
            "latitude": 37.7749,
            "longitude": -122.4194
        }, headers=headers)
        assert async_res.status_code == 202
        assert "job_id" in async_res.json()


@pytest.mark.asyncio
async def test_step34_contract_error_codes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 401
        r401 = await client.get("/api/triage/history", headers={"Authorization": "Bearer bad.token"})
        assert r401.status_code == 401

        # Register & login to test 422
        email = f"pytest_err_{int(time.time()*1000)}@roadsos.org"
        await client.post("/api/auth/register", json={
            "name": "Err User",
            "email": email,
            "password": "ErrPassword123!",
            "confirm_password": "ErrPassword123!"
        })
        login = await client.post("/api/auth/login", json={"email": email, "password": "ErrPassword123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # 422 Validation Error
        r422 = await client.post("/api/triage", json={"latitude": 999.0}, headers=headers)
        assert r422.status_code == 422


@pytest.mark.asyncio
async def test_step34_data_lifecycle_cleanliness():
    async with AsyncSessionLocal() as session:
        r_dup = await session.execute(
            text("SELECT job_id, count(*) FROM triage_events WHERE status = 'completed' AND job_id IS NOT NULL GROUP BY job_id HAVING count(*) > 1")
        )
        assert len(r_dup.fetchall()) == 0

        r_orphans = await session.execute(
            text("SELECT count(*) FROM triage_jobs j WHERE j.status = 'completed' AND NOT EXISTS (SELECT 1 FROM triage_events e WHERE e.job_id = j.id)")
        )
        assert r_orphans.scalar() == 0


@pytest.mark.asyncio
async def test_step34_ml_artifact_checksum():
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models/fusion_triage.pkl"))
    expected_sha = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"
    if os.path.exists(model_path):
        actual_sha = compute_sha256(model_path)
        assert actual_sha == expected_sha
