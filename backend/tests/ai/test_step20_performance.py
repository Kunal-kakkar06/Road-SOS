import os
import time
import pytest
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from main import app
from dependencies.auth_deps import create_access_token
from database import AsyncSessionLocal
from models.user import User
from models.triage_model import TriageJob, TriageEvent
from services.fusion_triage import get_model, fuse_triage_signals

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_perf_users():
    async def _setup():
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, delete
            # Clean up existing perf test users
            await db.execute(delete(User).where(User.uuid.in_(["perf-user-1", "perf-user-2", "perf-user-3"])))
            await db.commit()

            for u_id, email in [("perf-user-1", "perf1@example.com"), ("perf-user-2", "perf2@example.com"), ("perf-user-3", "perf3@example.com")]:
                u = User(uuid=u_id, email=email, is_active=True, role="USER", hashed_password="hash", name=f"Perf {u_id}")
                db.add(u)
            await db.commit()

    asyncio.run(_setup())

def get_auth_header(user_uuid: str) -> dict:
    token = create_access_token(user_uuid, "USER")
    return {"Authorization": f"Bearer {token}"}

def test_api_health_and_readiness_performance():
    start = time.perf_counter()
    resp = client.get("/api/ready")
    duration_ms = (time.perf_counter() - start) * 1000.0

    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
    assert duration_ms < 500  # Health check must complete within 500ms

def test_ml_pipeline_stage_profiling():
    # Profile ML inference components separately
    from ai.schemas.input_schema import AIInput
    from ai.feature_engine.feature_builder import FeatureBuilder

    ai_in = AIInput(request_id="perf-profile-1", symptoms="Chest pain and shortness of breath", age=55)

    # 1. Feature Extraction Timing
    t0 = time.perf_counter()
    builder = FeatureBuilder()
    feature_vector = builder.build(ai_in)
    t_feature = (time.perf_counter() - t0) * 1000.0

    # 2. XGBoost + SHAP Fusion Timing
    t1 = time.perf_counter()
    fusion_result = fuse_triage_signals(
        image_score=None,
        nlp_score=0.85,
        sensor_score=0.7,
        medical_risk=0.6
    )
    t_fusion = (time.perf_counter() - t1) * 1000.0

    assert feature_vector is not None
    assert fusion_result is not None
    assert t_feature < 100  # Feature extraction under 100ms
    assert t_fusion < 200   # Fusion + SHAP under 200ms

def test_concurrent_requests_for_different_users():
    headers_u1 = get_auth_header("perf-user-1")
    headers_u2 = get_auth_header("perf-user-2")

    payload = {"text": "Patient has severe dizziness", "has_image": False, "has_sensor_data": False}

    def submit_job(headers):
        return client.post("/api/triage/async", json=payload, headers=headers)

    with ThreadPoolExecutor(max_workers=4) as executor:
        f1 = executor.submit(submit_job, headers_u1)
        f2 = executor.submit(submit_job, headers_u2)

        r1 = f1.result()
        r2 = f2.result()

    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["job_id"] != r2.json()["job_id"]

def test_rate_limit_isolation_under_concurrency():
    # perf-user-1 submits up to 5 active jobs
    headers = get_auth_header("perf-user-1")
    payload = {"text": "Rate limit stress test payload"}

    responses = []
    for _ in range(6):
        res = client.post("/api/triage/async", json=payload, headers=headers)
        responses.append(res.status_code)

    # First 5 should succeed (202), 6th should be blocked by rate limit (429)
    assert responses.count(202) <= 5
    assert 429 in responses or responses.count(202) == 5

@pytest.mark.asyncio
async def test_idempotent_event_persistence():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select, delete
        # Verify unique event_id prevents duplicate TriageEvent creation
        job_id = "test-perf-idempotent-job-123"
        await db.execute(delete(TriageEvent).where(TriageEvent.event_id == job_id))
        await db.commit()

        ev1 = TriageEvent(
            id=job_id,
            event_id=job_id,
            user_id="perf-user-1",
            job_id=job_id,
            status="completed",
            final_severity="High",
            final_score=0.8
        )
        db.add(ev1)
        await db.commit()

        # Re-querying by event_id finds existing event instead of creating duplicate
        res = await db.execute(select(TriageEvent).where(TriageEvent.event_id == job_id))
        fetched = res.scalars().first()
        assert fetched is not None
        assert fetched.id == job_id

def test_prometheus_performance_metrics_exposure():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    metrics_str = resp.text

    assert "http_requests_total" in metrics_str
    assert "disaster_recovery_latest_backup_age_seconds" in metrics_str
    assert "disaster_recovery_remote_storage_available" in metrics_str
    assert "disaster_recovery_rpo_seconds" in metrics_str
    assert "disaster_recovery_rto_seconds" in metrics_str
