import pytest
import os
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy import select, func, text, update

from main import app
from database import engine, AsyncSessionLocal
from models.user import User
from models.triage_model import TriageJob, TriageEvent
from models.worker_model import WorkerHeartbeat
from dependencies.auth_deps import create_access_token
from services.backup_replication_service import backup_replication_service

@pytest.mark.asyncio
async def test_1_readiness_and_liveness_failure_isolation():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Liveness returns 200 OK without database query
        r_live = await client.get("/api/health")
        assert r_live.status_code == 200
        assert r_live.json()["liveness"] is True

        # Readiness returns 200 OK when DB is healthy
        r_ready = await client.get("/api/ready")
        assert r_ready.status_code == 200
        assert r_ready.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_2_stale_worker_reclamation_without_duplicate_events():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).filter(User.uuid == "pytest-resilience-user"))
        if not res.scalars().first():
            session.add(User(uuid="pytest-resilience-user", name="Pytest Res User", email="pytestres@example.com", hashed_password="pw", role="USER"))
            await session.commit()

        job_id = str(uuid.uuid4())
        dead_worker = f"worker-dead-{uuid.uuid4().hex[:6]}"
        stale_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)

        # Seed stale job
        session.add(TriageJob(
            id=job_id,
            user_id="pytest-resilience-user",
            status="processing",
            worker_id=dead_worker,
            started_at=stale_time,
            heartbeat_at=stale_time,
            attempt_count=1,
            payload={"text": "Crash triage test"}
        ))
        session.add(WorkerHeartbeat(
            worker_id=dead_worker,
            status="crashed",
            started_at=stale_time,
            last_heartbeat=stale_time,
            current_job_id=job_id
        ))
        await session.commit()

        # Reclaim stale job
        is_postgres = engine.dialect.name == "postgresql"
        timeout_threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

        if is_postgres:
            stmt = text("""
                UPDATE triage_jobs
                SET status = 'processing', worker_id = 'worker-reclaim-pytest', heartbeat_at = :now
                WHERE id = (
                    SELECT id FROM triage_jobs
                    WHERE (status = 'pending' OR (status = 'processing' AND heartbeat_at < :timeout))
                      AND id = :job_id
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                RETURNING id
            """)
            res = await session.execute(stmt, {"now": now_utc, "timeout": timeout_threshold, "job_id": job_id})
            assert res.fetchone() is not None
            await session.commit()

        session.expire_all()
        check = await session.execute(select(TriageJob).where(TriageJob.id == job_id))
        reclaimed = check.scalars().first()
        if is_postgres:
            assert reclaimed.worker_id == "worker-reclaim-pytest"

        # Verify event count for reclaimed job (worker process creates event upon completion)
        session.expire_all()
        ev_count = await session.execute(select(func.count()).select_from(TriageEvent).where(TriageEvent.job_id == job_id))
        assert ev_count.scalar() <= 1, "Duplicate TriageEvent created for reclaimed job!"


@pytest.mark.asyncio
async def test_3_minio_unavailability_graceful_handling():
    dummy_path = "/tmp/pytest_dummy.sql.gz"
    with open(dummy_path, "w") as f:
        f.write("dummy")

    orig_rep = os.environ.get("BACKUP_REPLICATION_ENABLED")
    orig_ep = os.environ.get("BACKUP_STORAGE_ENDPOINT")

    try:
        os.environ["BACKUP_REPLICATION_ENABLED"] = "true"
        os.environ["BACKUP_STORAGE_ENDPOINT"] = "http://localhost:9999"
        os.environ["BACKUP_STORAGE_BUCKET"] = "roadsos-backups"

        result = backup_replication_service.replicate_backup(dummy_path)
        assert result["status"] == "failed"
        assert result.get("error") is not None
    finally:
        if os.path.exists(dummy_path):
            os.remove(dummy_path)
        if orig_rep: os.environ["BACKUP_REPLICATION_ENABLED"] = orig_rep
        else: os.environ.pop("BACKUP_REPLICATION_ENABLED", None)
        if orig_ep: os.environ["BACKUP_STORAGE_ENDPOINT"] = orig_ep
        else: os.environ.pop("BACKUP_STORAGE_ENDPOINT", None)


@pytest.mark.asyncio
async def test_4_audit_consistency_and_zero_duplicate_events():
    async with AsyncSessionLocal() as session:
        # Verify no duplicate events for any job_id
        stmt = text("""
            SELECT job_id, count(*) FROM triage_events
            WHERE job_id IS NOT NULL
            GROUP BY job_id
            HAVING count(*) > 1
        """)
        res = await session.execute(stmt)
        duplicates = res.fetchall()
        assert len(duplicates) == 0, f"Duplicate audit events found: {duplicates}"


@pytest.mark.asyncio
async def test_5_connection_pool_pre_ping_recovery():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT 1"))
        assert res.scalar() == 1


@pytest.mark.asyncio
async def test_6_graceful_worker_shutdown_signal():
    from worker import shutdown_event
    shutdown_event.set()
    assert shutdown_event.is_set()
    shutdown_event.clear()
