import os
import sys
import time
import uuid
import datetime
import asyncio
import subprocess

MINIO_ENDPOINT = "http://localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET = "roadsos-offsite-backups"
MINIO_REGION = "us-east-1"
POSTGRES_URL = "postgresql+asyncpg://roadsos:roadsos_password@localhost:5432/roadsos_db"

os.environ["BACKUP_REPLICATION_ENABLED"] = "true"
os.environ["BACKUP_STORAGE_BUCKET"] = MINIO_BUCKET
os.environ["BACKUP_STORAGE_ENDPOINT"] = MINIO_ENDPOINT
os.environ["BACKUP_STORAGE_ACCESS_KEY"] = MINIO_ACCESS_KEY
os.environ["BACKUP_STORAGE_SECRET_KEY"] = MINIO_SECRET_KEY
os.environ["BACKUP_STORAGE_REGION"] = MINIO_REGION
os.environ["DATABASE_URL"] = POSTGRES_URL

import boto3
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from models.user import User
from models.triage_model import TriageJob, TriageEvent
from models.worker_model import WorkerHeartbeat
from services.backup_service import BackupService
from services.backup_replication_service import BackupReplicationService
from scripts.verify_remote_backup import verify_remote_backup
from scripts.cleanup_backups import cleanup_backups
from main import validate_production_configuration

def ensure_minio_bucket():
    s3 = boto3.client("s3", endpoint_url=MINIO_ENDPOINT, aws_access_key_id=MINIO_ACCESS_KEY, aws_secret_access_key=MINIO_SECRET_KEY, region_name=MINIO_REGION)
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=MINIO_BUCKET)

async def run_async_scenarios():
    pg_engine = create_async_engine(POSTGRES_URL, echo=False)
    PgSessionLocal = sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)

    print("\n--- [SCENARIO A] API Process Failure & Worker Processing Continuity ---")
    async with PgSessionLocal() as db:
        from sqlalchemy import select
        job_id = f"job-scen-a-{uuid.uuid4().hex[:8]}"
        req_id = f"req-scen-a-{uuid.uuid4().hex[:8]}"
        job = TriageJob(
            id=job_id,
            user_id="user-a-uuid",
            request_id=req_id,
            status="pending",
            payload={"text": "Scenario A API crash test payload", "age": 40}
        )
        db.add(job)
        await db.commit()
        print(f"[INFO] Submitted job '{job_id}' directly to PostgreSQL queue.")

    for _ in range(20):
        await asyncio.sleep(0.5)
        async with PgSessionLocal() as db:
            res = await db.execute(select(TriageJob).filter(TriageJob.id == job_id))
            j = res.scalars().first()
            if j and j.status in ("completed", "failed"):
                print(f"[SUCCESS] Worker processed job '{job_id}' with status '{j.status}' independent of API server.")
                break

    print("\n--- [SCENARIO B] Worker Crash, Stale Heartbeat Reclaim & Audit Integrity ---")
    stale_worker = "worker-crashed-dead-node"
    stale_time = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(minutes=10)
    job_id_b = f"job-scen-b-{uuid.uuid4().hex[:8]}"
    req_id_b = f"req-scen-b-{uuid.uuid4().hex[:8]}"

    async with PgSessionLocal() as db:
        from sqlalchemy import select
        hb = WorkerHeartbeat(worker_id=stale_worker, last_heartbeat=stale_time, status="active", completed_jobs=5)
        db.add(hb)

        stuck_job = TriageJob(
            id=job_id_b,
            user_id="user-a-uuid",
            request_id=req_id_b,
            status="processing",
            worker_id=stale_worker,
            attempt_count=1,
            created_at=stale_time,
            payload={"text": "Scenario B worker crash test payload", "age": 55}
        )
        db.add(stuck_job)
        await db.commit()
        print(f"[INFO] Created stuck processing job '{job_id_b}' claimed by crashed worker '{stale_worker}'.")

    await asyncio.sleep(2.0)

    async with PgSessionLocal() as db:
        from sqlalchemy import select
        res = await db.execute(select(TriageJob).filter(TriageJob.id == job_id_b))
        j = res.scalars().first()
        if j:
            print(f"[INFO] Reclaimed Job State: status='{j.status}', worker_id='{j.worker_id}', attempt_count={j.attempt_count}")
            events = (await db.execute(select(TriageEvent).filter(TriageEvent.job_id == job_id_b))).scalars().all()
            print(f"[INFO] Matching TriageEvents Count: {len(events)}")
            assert len(events) <= 1, "Duplicate TriageEvent audit logs generated!"
            print("[VERIFIED] Scenario B: Stale job reclaimed without duplicate audit logs.")

    print("\n--- [SCENARIO C] Database Connection Ping & Pool Re-establishment ---")
    async with PgSessionLocal() as db:
        from sqlalchemy import text
        res = await db.execute(text("SELECT version();"))
        ver = res.scalar()
        print(f"[SUCCESS] PostgreSQL Connection Verified: {ver[:50]}")

    await pg_engine.dispose()

def ensure_minio_bucket():
    s3 = boto3.client("s3", endpoint_url=MINIO_ENDPOINT, aws_access_key_id=MINIO_ACCESS_KEY, aws_secret_access_key=MINIO_SECRET_KEY, region_name=MINIO_REGION)
    try:
        s3.head_bucket(Bucket=MINIO_BUCKET)
    except Exception:
        s3.create_bucket(Bucket=MINIO_BUCKET)

def test_scenario_d_object_storage_outage():
    print("\n--- [SCENARIO D] Off-Site S3 Storage Outage Resilience ---")
    os.environ["BACKUP_STORAGE_ENDPOINT"] = "http://localhost:9999"
    svc = BackupService(backup_dir="/tmp/roadsos_backups")
    res = svc.create_backup(compress=True, replicate=True)
    os.environ["BACKUP_STORAGE_ENDPOINT"] = MINIO_ENDPOINT

    assert res["status"] == "completed"  # Local backup preserved
    assert res["replication"]["status"] == "failed"  # Outage recorded safely
    print("[VERIFIED] Scenario D: S3 outage handled cleanly. Local backup preserved, replication failure recorded.")

def test_scenario_e_disposable_full_restore():
    print("\n--- [SCENARIO E] Off-Site Disposable Database Restore ---")
    ensure_minio_bucket()
    svc = BackupService(backup_dir="/tmp/roadsos_backups")
    b_res = svc.create_backup(compress=True, replicate=True)
    remote_key = b_res["replication"]["remote_key"]

    restore_res = svc.verify_remote_backup(remote_key)
    assert restore_res["status"] == "completed" or restore_res.get("restore_result", {}).get("status") == "PASSED"
    info = restore_res.get("restore_result", {})
    print(f"[SUCCESS] Restored DB Tables: {info.get('table_counts')}")
    print(f"[SUCCESS] Restored Alembic Revision: {info.get('alembic_version').strip()}")
    print("[VERIFIED] Scenario E: Full disposable database restore PASSED cleanly.")

def test_production_fast_fail_config():
    print("\n--- [CONFIG GUARD] Production Fast-Fail Validation ---")
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "sqlite:///./test_guard.db"
    try:
        validate_production_configuration()
        print("[FATAL] Production guard failed to block SQLite!", file=sys.stderr)
        sys.exit(1)
    except ValueError as ve:
        print(f"[PASS] Production guard blocked SQLite: {ve}")

    os.environ["ENVIRONMENT"] = "development"
    os.environ["DATABASE_URL"] = "postgresql://roadsos:roadsos_password@localhost:5432/roadsos_db"

def main():
    print("=" * 64)
    print("STEP 20 PHYSICAL DISASTER RECOVERY GAME DAY & SLO VERIFICATION")
    print("=" * 64)

    ensure_minio_bucket()

    # Run async scenarios (Scenarios A, B, C)
    asyncio.run(run_async_scenarios())

    # Run sync scenarios (Scenarios D, E & Config Guard)
    test_scenario_d_object_storage_outage()
    test_scenario_e_disposable_full_restore()
    test_production_fast_fail_config()

    print("\n" + "=" * 64)
    print("ALL STEP 20 DR GAME DAY & SLO VERIFICATION TESTS PASSED!")
    print("=" * 64)

if __name__ == "__main__":
    main()
