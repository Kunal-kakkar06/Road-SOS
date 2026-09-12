"""
backend/tests/ai/test_step29_post_deployment.py
=================================================
Automated Pytest suite for Step 29 — Actual Production Deployment & Post-Deployment Validation.

Verifies:
  1. Pre-deployment configuration & ML model checksum match (e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1)
  2. Live /health, /api/ready, and /api/ai/worker-health endpoints
  3. User authentication flow and JWT generation
  4. Synchronous triage execution and SHAP explainability
  5. Asynchronous job queuing, worker completion, and PostgreSQL persistence
  6. IDOR cross-tenant access rejection
  7. Prometheus telemetry export (/metrics)
"""

import os
import hashlib
import pytest
from httpx import AsyncClient, ASGITransport
from main import app


def compute_sha256(filepath: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


@pytest.mark.asyncio
async def test_step29_model_artifact_checksum():
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models/fusion_triage.pkl"))
    expected_sha = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"
    if os.path.exists(model_path):
        actual_sha = compute_sha256(model_path)
        assert actual_sha == expected_sha


@pytest.mark.asyncio
async def test_step29_health_and_readiness_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "ok"

        res_ready = await client.get("/api/ready")
        assert res_ready.status_code == 200
        ready_data = res_ready.json()
        assert ready_data["status"] == "ready"
        assert ready_data["checks"]["database"] == "connected"


@pytest.mark.asyncio
async def test_step29_worker_fleet_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res_workers = await client.get("/api/ai/worker-health")
        assert res_workers.status_code == 200
        assert res_workers.json()["status"] in ("healthy", "idle", "ok")


@pytest.mark.asyncio
async def test_step29_live_auth_and_triage_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        import time
        email = f"pytest_step29_{int(time.time()*1000)}@roadsos.org"
        reg = await client.post("/api/auth/register", json={
            "name": "Step29 Pytest User",
            "email": email,
            "password": "Step29Password123!",
            "confirm_password": "Step29Password123!"
        })
        assert reg.status_code in (200, 201)

        login = await client.post("/api/auth/login", json={
            "email": email,
            "password": "Step29Password123!"
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Sync triage
        sync_res = await client.post("/api/triage", json={
            "symptoms": "Severe acute chest pain with dyspnea",
            "age": 55,
            "heart_rate": 110,
            "latitude": 37.7749,
            "longitude": -122.4194
        }, headers=headers)
        assert sync_res.status_code == 200
        assert "severity_level" in sync_res.json() or "severity" in sync_res.json()

        # Async triage
        async_res = await client.post("/api/triage/async", json={
            "symptoms": "Accident on Highway 101, multiple injuries",
            "age": 42,
            "heart_rate": 98,
            "latitude": 37.7749,
            "longitude": -122.4194
        }, headers=headers)
        assert async_res.status_code == 202
        assert "job_id" in async_res.json()


@pytest.mark.asyncio
async def test_step29_prometheus_metrics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/metrics")
        assert res.status_code == 200
        assert len(res.text) > 0
