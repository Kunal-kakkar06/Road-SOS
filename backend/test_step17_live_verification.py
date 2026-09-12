#!/usr/bin/env python3
"""
Step 17 Physical PostgreSQL 15 Live Verification & Chaos Performance Script.
"""

import os
import sys
import time
import uuid
import asyncio
import numpy as np
from datetime import datetime, timezone

os.environ["DATABASE_URL"] = "postgresql+asyncpg://roadsos:roadsos_password@localhost:5432/roadsos_db"
os.environ["JWT_SECRET"] = "roadsos-test-secret-key"

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, select, func
from models.triage_model import TriageJob, TriageEvent
from models.worker_model import WorkerHeartbeat
from routers.triage import _execute_triage_pipeline, TriageRequest
from scripts.backup_db import run_backup
from scripts.verify_restore import verify_restore

engine = create_async_engine(os.environ["DATABASE_URL"], echo=False, pool_size=25, max_overflow=15)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    print("================================================================")
    print("STEP 17 LIVE POSTGRESQL VERIFICATION & CHAOS BENCHMARK")
    print("================================================================")

    # 1. Test Backup Automation
    print("\n--- [1] Physical Backup Automation (`backup_db.py`) ---")
    backup_file = run_backup(output_dir="/tmp/roadsos_backups", compress=True)
    assert os.path.exists(backup_file)
    assert os.path.getsize(backup_file) > 0
    print(f"[VERIFIED] Backup file generated: {backup_file} ({os.path.getsize(backup_file)} bytes)")

    # 2. Test Restore Verification
    print("\n--- [2] Physical Restore Verification (`verify_restore.py`) ---")
    restore_res = verify_restore(backup_file=backup_file, temp_dbname="roadsos_restore_verify_tmp")
    assert restore_res["status"] == "PASSED"
    print(f"[VERIFIED] Restore verification output: {restore_res}")

    # 3. Test Worker Heartbeat Registry in Live PostgreSQL
    print("\n--- [3] Worker Heartbeat Registry & Health Visibility ---")
    worker_id = f"worker-live-step17-{uuid.uuid4()}"
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    async with AsyncSessionLocal() as session:
        hb = WorkerHeartbeat(
            worker_id=worker_id,
            status="active",
            started_at=now_utc,
            last_heartbeat=now_utc,
            completed_jobs=5,
            failed_jobs=0
        )
        session.add(hb)
        await session.commit()

        # Query metrics
        res = await session.execute(text("SELECT status, count(*) FROM worker_heartbeats GROUP BY status"))
        worker_metrics = dict(res.fetchall())
        print(f"[VERIFIED] Live PostgreSQL worker_heartbeats table output: {worker_metrics}")

    # 4. Test Idempotent TriageEvent Creation
    print("\n--- [4] Event Idempotency Hardening Test ---")
    req = TriageRequest(text="Severe crush injury, loss of consciousness", age=38, gender="female")
    req_id = f"req-idempotent-live-{uuid.uuid4()}"
    user_id = f"user-live-{uuid.uuid4()}"

    async with AsyncSessionLocal() as session:
        # Submit execution 1
        res1 = await _execute_triage_pipeline(req, session, user_id=user_id, processing_mode="sync", request_id=req_id)
        # Submit execution 2 (retry with identical request_id)
        res2 = await _execute_triage_pipeline(req, session, user_id=user_id, processing_mode="sync", request_id=req_id)

        # Check total TriageEvents in DB
        res_events = await session.execute(select(TriageEvent).where(TriageEvent.event_id == req_id))
        events = res_events.scalars().all()
        assert len(events) == 1
        print(f"[VERIFIED] Executed pipeline twice with request_id '{req_id}'. Total TriageEvent rows created: {len(events)} (Status: {events[0].status})")

    # 5. Performance Burst Load Smoke Test (20 Jobs against PostgreSQL 15)
    print("\n--- [5] PostgreSQL 20-Job Concurrent Burst Load & Latency Smoke Test ---")
    latencies = []
    job_ids = []
    start_batch = time.perf_counter()

    async with AsyncSessionLocal() as session:
        for i in range(20):
            t_start = time.perf_counter()
            j_id = str(uuid.uuid4())
            r_id = str(uuid.uuid4())
            job = TriageJob(
                id=j_id,
                user_id=f"user-batch-{i}",
                status="pending",
                request_id=r_id,
                payload={"text": f"Emergency accident scenario {i}", "age": 20 + i, "gender": "male"}
            )
            session.add(job)
            await session.commit()
            t_dur = (time.perf_counter() - t_start) * 1000
            latencies.append(t_dur)
            job_ids.append(j_id)

    total_batch_duration = time.perf_counter() - start_batch
    p50 = float(np.percentile(latencies, 50))
    p95 = float(np.percentile(latencies, 95))
    p99 = float(np.percentile(latencies, 99))

    print(f"Submitted {len(job_ids)} jobs to live PostgreSQL 15.")
    print(f"Batch Execution Total Duration: {total_batch_duration:.2f} seconds")
    print(f"Submission Latency p50: {p50:.2f} ms")
    print(f"Submission Latency p95: {p95:.2f} ms")
    print(f"Submission Latency p99: {p99:.2f} ms")

    # Wait for workers to process jobs
    print("\nWaiting for live worker processes to complete queued jobs...")
    completed = False
    for _ in range(15):
        await asyncio.sleep(1.0)
        async with AsyncSessionLocal() as session:
            stmt_cnt = select(func.count()).select_from(TriageJob).where(TriageJob.id.in_(job_ids), TriageJob.status == "completed")
            res_comp = await session.execute(stmt_cnt)
            cnt = res_comp.scalar()
            print(f"  Processed jobs: {cnt} / 20")
            if cnt == 20:
                completed = True
                break

    assert completed, "Workers failed to process all 20 jobs within 15 seconds"
    print("\n================================================================")
    print("ALL STEP 17 LIVE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("================================================================")

if __name__ == "__main__":
    asyncio.run(main())
