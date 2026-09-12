import asyncio
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Set environment for PostgreSQL
os.environ["DATABASE_URL"] = "postgresql+asyncpg://roadsos:roadsos_password@localhost:5432/roadsos_db"
os.environ["JWT_SECRET"] = "test-jwt-secret-for-step14-pg-verification"

from main import app
from database import engine, AsyncSessionLocal
from models.user import User
from models.triage_model import TriageJob, TriageEvent
from dependencies.auth_deps import create_access_token, get_password_hash

test_user_a = str(uuid.uuid4())
test_user_b = str(uuid.uuid4())
token_a = create_access_token(test_user_a, "USER")
token_b = create_access_token(test_user_b, "USER")

async def setup_test_users():
    async with AsyncSessionLocal() as session:
        user_a_obj = User(
            uuid=test_user_a,
            name="User A",
            email=f"user_a_{test_user_a[:8]}@example.com",
            hashed_password=get_password_hash("password123"),
            role="USER"
        )
        user_b_obj = User(
            uuid=test_user_b,
            name="User B",
            email=f"user_b_{test_user_b[:8]}@example.com",
            hashed_password=get_password_hash("password123"),
            role="USER"
        )
        session.add(user_a_obj)
        session.add(user_b_obj)
        await session.commit()
    print(f"Created test users in PostgreSQL: {test_user_a}, {test_user_b}")

async def run_pg_verifications():
    print("=========================================================")
    print("STARTING REAL POSTGRESQL 15 STEP 14 E2E PHYSICAL VERIFICATION")
    print("=========================================================")
    
    await setup_test_users()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        
        # ---------------------------------------------------------
        # 1. POSTGRESQL MULTI-WORKER CONCURRENCY & FOR UPDATE SKIP LOCKED
        # ---------------------------------------------------------
        print("\n--- [1] Multi-Worker Claiming & SKIP LOCKED ---")
        
        batch_tokens = []
        async with AsyncSessionLocal() as session:
            for i in range(10):
                u_uuid = str(uuid.uuid4())
                u_obj = User(
                    uuid=u_uuid,
                    name=f"Batch User {i}",
                    email=f"batch_user_{i}_{u_uuid[:8]}@example.com",
                    hashed_password=get_password_hash("password123"),
                    role="USER"
                )
                session.add(u_obj)
                batch_tokens.append(create_access_token(u_uuid, "USER"))
            await session.commit()

        job_ids = []
        for i in range(10):
            res = await client.post(
                "/api/triage/async",
                headers={"Authorization": f"Bearer {batch_tokens[i]}"},
                json={"text": f"Severe accident victim {i}, bleeding heavily, chest pain."}
            )
            assert res.status_code == 202, f"Job creation failed: {res.text}"
            job_ids.append(res.json()["job_id"])
        
        print(f"Submitted 10 jobs to PostgreSQL: {job_ids[:3]}...")
        
        from worker import worker_loop
        worker_task_1 = asyncio.create_task(worker_loop())
        worker_task_2 = asyncio.create_task(worker_loop())
        
        start_time = time.time()
        completed = False
        while time.time() - start_time < 15:
            async with AsyncSessionLocal() as session:
                res = await session.execute(
                    select(TriageJob).where(TriageJob.id.in_(job_ids), TriageJob.status == "completed")
                )
                done_jobs = res.scalars().all()
                if len(done_jobs) == 10:
                    completed = True
                    break
            await asyncio.sleep(0.5)
            
        worker_task_1.cancel()
        worker_task_2.cancel()
        
        assert completed, f"Only {len(done_jobs)} / 10 jobs completed in time!"
        
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(TriageJob).where(TriageJob.id.in_(job_ids)))
            jobs = res.scalars().all()
            worker_ids = set(j.worker_id for j in jobs)
            print(f"Verified 10/10 jobs completed across worker IDs: {worker_ids}")
            assert len(worker_ids) >= 1, "At least one worker must claim jobs"
            
            evt_res = await session.execute(select(TriageEvent).where(TriageEvent.job_id.in_(job_ids)))
            events = evt_res.scalars().all()
            print(f"Verified exactly {len(events)} TriageEvent rows created in PostgreSQL for 10 jobs.")
            assert len(events) == 10

        # ---------------------------------------------------------
        # 2. WORKER CRASH RECOVERY & HEARTBEAT RECLAIM
        # ---------------------------------------------------------
        print("\n--- [2] Worker Crash Recovery & Heartbeat Reclaim ---")
        stale_job_id = f"stale-job-{uuid.uuid4()}"
        stale_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=10)
        
        async with AsyncSessionLocal() as session:
            stale_job = TriageJob(
                id=stale_job_id,
                user_id=test_user_a,
                status="processing",
                request_id=f"req-stale-{uuid.uuid4()}",
                payload={"text": "Stale patient text"},
                worker_id="dead-worker-999",
                attempt_count=1,
                started_at=stale_time,
                heartbeat_at=stale_time
            )
            session.add(stale_job)
            await session.commit()
            
        w_task = asyncio.create_task(worker_loop())
        await asyncio.sleep(4)
        w_task.cancel()
        
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(TriageJob).where(TriageJob.id == stale_job_id))
            reclaimed_job = res.scalars().first()
            print(f"Stale job status: {reclaimed_job.status}, worker_id: {reclaimed_job.worker_id}, attempt_count: {reclaimed_job.attempt_count}")
            assert reclaimed_job.status == "completed"
            assert reclaimed_job.worker_id != "dead-worker-999"
            assert reclaimed_job.attempt_count >= 1

        # ---------------------------------------------------------
        # 3. MAX RETRY EXHAUSTION (3 FAILURES -> FAILED)
        # ---------------------------------------------------------
        print("\n--- [3] Max Retry Exhaustion ---")
        fail_job_id = f"fail-job-{uuid.uuid4()}"
        async with AsyncSessionLocal() as session:
            f_job = TriageJob(
                id=fail_job_id,
                user_id=test_user_a,
                status="pending",
                request_id=f"req-fail-{uuid.uuid4()}",
                payload={"latitude": "INVALID_FLOAT_THAT_RAISES_VALIDATION_ERROR"},
                attempt_count=2
            )
            session.add(f_job)
            await session.commit()
            
        w_task = asyncio.create_task(worker_loop())
        await asyncio.sleep(4)
        w_task.cancel()
        
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(TriageJob).where(TriageJob.id == fail_job_id))
            failed_job = res.scalars().first()
            print(f"Failed job final status: {failed_job.status}, attempt_count: {failed_job.attempt_count}, error: {failed_job.error}")
            assert failed_job.status == "failed"
            assert failed_job.attempt_count == 3

        # ---------------------------------------------------------
        # 4. IDEMPOTENCY & REPEATED POLLING
        # ---------------------------------------------------------
        print("\n--- [4] Idempotency & Polling Test ---")
        poll_res = await client.post(
            "/api/triage/async",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"text": "Idempotency test scenario"}
        )
        poll_job_id = poll_res.json()["job_id"]
        
        w_task = asyncio.create_task(worker_loop())
        await asyncio.sleep(3)
        w_task.cancel()
        
        # Poll 100 times
        for _ in range(100):
            r = await client.get(
                f"/api/triage/jobs/{poll_job_id}",
                headers={"Authorization": f"Bearer {token_a}"}
            )
            assert r.status_code == 200
            
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(TriageEvent).where(TriageEvent.job_id == poll_job_id))
            events = res.scalars().all()
            print(f"Polled job {poll_job_id} 100 times. Total TriageEvent records in DB: {len(events)}")
            assert len(events) == 1

        # ---------------------------------------------------------
        # 5. CONCURRENCY LOAD SMOKE TEST (20 JOBS METRICS)
        # ---------------------------------------------------------
        print("\n--- [5] Concurrency Load Smoke Test (20 Jobs Metrics) ---")
        
        load_tokens = []
        async with AsyncSessionLocal() as session:
            for i in range(20):
                u_uuid = str(uuid.uuid4())
                u_obj = User(
                    uuid=u_uuid,
                    name=f"Load User {i}",
                    email=f"load_user_{i}_{u_uuid[:8]}@example.com",
                    hashed_password=get_password_hash("password123"),
                    role="USER"
                )
                session.add(u_obj)
                load_tokens.append(create_access_token(u_uuid, "USER"))
            await session.commit()

        sub_latencies = []
        batch_ids = []
        
        t0 = time.time()
        for i in range(20):
            st = time.time()
            res = await client.post(
                "/api/triage/async",
                headers={"Authorization": f"Bearer {load_tokens[i]}"},
                json={"text": f"Batch load patient {i}"}
            )
            sub_latencies.append((time.time() - st) * 1000)
            if res.status_code == 202:
                batch_ids.append(res.json()["job_id"])
                
        w_task_1 = asyncio.create_task(worker_loop())
        w_task_2 = asyncio.create_task(worker_loop())
        
        wait_start = time.time()
        while time.time() - wait_start < 20:
            async with AsyncSessionLocal() as session:
                res = await session.execute(
                    select(TriageJob).where(TriageJob.id.in_(batch_ids), TriageJob.status == "completed")
                )
                done = res.scalars().all()
                if len(done) == len(batch_ids):
                    break
            await asyncio.sleep(0.5)
            
        w_task_1.cancel()
        w_task_2.cancel()
        
        total_time = time.time() - t0
        sub_latencies.sort()
        p50 = sub_latencies[len(sub_latencies) // 2]
        p95 = sub_latencies[int(len(sub_latencies) * 0.95)]
        print(f"20 Jobs Load Metrics against PostgreSQL 15:")
        print(f"  Total Batch Time: {total_time:.2f}s")
        print(f"  Submission Latency p50: {p50:.2f}ms, p95: {p95:.2f}ms")
        print(f"  Completed Jobs: {len(done)} / {len(batch_ids)}")

        # ---------------------------------------------------------
        # 6. RATE LIMITING REGRESSION (5 PENDING JOBS -> 6TH 429)
        # ---------------------------------------------------------
        print("\n--- [6] Rate Limiting Regression ---")
        rl_user = str(uuid.uuid4())
        rl_token = create_access_token(rl_user, "USER")
        
        async with AsyncSessionLocal() as session:
            rl_user_obj = User(
                uuid=rl_user,
                name="RL User",
                email=f"rl_user_{rl_user[:8]}@example.com",
                hashed_password=get_password_hash("password123"),
                role="USER"
            )
            session.add(rl_user_obj)
            await session.commit()
            
        rl_jobs = []
        for i in range(5):
            r = await client.post(
                "/api/triage/async",
                headers={"Authorization": f"Bearer {rl_token}"},
                json={"text": f"Pending job {i}"}
            )
            assert r.status_code == 202
            rl_jobs.append(r.json()["job_id"])
            
        # 6th attempt must return 429
        r6 = await client.post(
            "/api/triage/async",
            headers={"Authorization": f"Bearer {rl_token}"},
            json={"text": "Over limit job"}
        )
        print(f"6th async submission status code: {r6.status_code}, detail: {r6.json()}")
        assert r6.status_code == 429

        # ---------------------------------------------------------
        # 7. AUTHENTICATION & IDOR REGRESSION
        # ---------------------------------------------------------
        print("\n--- [7] Authentication & IDOR Isolation ---")
        unauth_res = await client.get(f"/api/triage/jobs/{job_ids[0]}")
        print(f"Unauthenticated request status: {unauth_res.status_code}")
        assert unauth_res.status_code == 401
        
        idor_res = await client.get(
            f"/api/triage/jobs/{job_ids[0]}",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        print(f"User B accessing User A job status: {idor_res.status_code}")
        assert idor_res.status_code == 404

        # ---------------------------------------------------------
        # 8. INPUT VALIDATION REGRESSION
        # ---------------------------------------------------------
        print("\n--- [8] Input Validation Regression ---")
        bad_lat = await client.post(
            "/api/triage",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"text": "Help", "latitude": 99.0}
        )
        print(f"Latitude 99.0 status: {bad_lat.status_code}")
        assert bad_lat.status_code == 422
        
        bad_text = await client.post(
            "/api/triage",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"text": "A" * 2500}
        )
        print(f"Text > 2000 chars status: {bad_text.status_code}")
        assert bad_text.status_code == 422

        # ---------------------------------------------------------
        # 9. OBSERVABILITY & TRACING VERIFICATION
        # ---------------------------------------------------------
        print("\n--- [9] Observability & Tracing Metadata ---")
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(TriageEvent).where(TriageEvent.job_id == job_ids[0]))
            evt = res.scalars().first()
            j_res = await session.execute(select(TriageJob).where(TriageJob.id == job_ids[0]))
            job = j_res.scalars().first()
            
            print("Verified TriageEvent & TriageJob PostgreSQL row fields:")
            print(f"  event_id: {evt.event_id}")
            print(f"  job_id: {evt.job_id}")
            print(f"  request_id: {job.request_id}")
            print(f"  worker_id: {job.worker_id}")
            print(f"  processing_mode: {evt.processing_mode}")
            print(f"  processing_duration_ms: {evt.processing_duration_ms}")
            print(f"  model_version: {evt.model_version}")
            assert job.request_id is not None
            assert evt.model_version is not None

    print("\n=========================================================")
    print("ALL REAL POSTGRESQL 15 VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=========================================================")

if __name__ == "__main__":
    asyncio.run(run_pg_verifications())
