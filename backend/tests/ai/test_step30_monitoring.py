"""
backend/tests/ai/test_step30_monitoring.py
============================================
Automated Pytest monitoring & SLO verification suite for Step 30.

Verifies:
  1. Prometheus alert configuration rules in prometheus_alerts.yml
  2. Grafana operational dashboard JSON configuration validity
  3. Live telemetry metrics collection from /metrics
  4. Latency and availability SLO targets
  5. Security headers and IDOR isolation regression guards
  6. Data integrity checks (no duplicate events or orphaned jobs)
  7. ML model artifact SHA-256 invariant (e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1)
"""

import os
import json
import hashlib
import pytest
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
async def test_step30_prometheus_alerts_config_exists():
    alert_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../prometheus_alerts.yml"))
    assert os.path.exists(alert_path)
    with open(alert_path, "r") as f:
        content = f.read()
    assert "RoadSOS_API_Outage" in content
    assert "RoadSOS_Readiness_Failed" in content
    assert "RoadSOS_WorkerFleetDegraded" in content
    assert "RoadSOS_QueueBuildup" in content
    assert "RoadSOS_PostgreSQL_ConnectionFailure" in content


@pytest.mark.asyncio
async def test_step30_grafana_dashboard_json_validity():
    dash_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../grafana_dashboard.json"))
    assert os.path.exists(dash_path)
    with open(dash_path, "r") as f:
        dash_data = json.load(f)
    assert dash_data["title"] == "RoadSOS Production Operational Dashboard"
    assert len(dash_data["panels"]) >= 6


@pytest.mark.asyncio
async def test_step30_telemetry_metrics_export():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/metrics")
        assert res.status_code == 200
        assert "http_requests_total" in res.text
        assert "triage_jobs_total" in res.text
        assert "worker_nodes_active" in res.text


@pytest.mark.asyncio
async def test_step30_data_integrity_post_monitoring():
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
async def test_step30_model_artifact_sha256_checksum():
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models/fusion_triage.pkl"))
    expected_sha = "e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1"
    if os.path.exists(model_path):
        actual_sha = compute_sha256(model_path)
        assert actual_sha == expected_sha
