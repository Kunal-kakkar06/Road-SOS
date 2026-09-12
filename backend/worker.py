import asyncio
import os
import uuid
import signal
import logging
from datetime import datetime, timedelta, timezone

# Load env before imports
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, update, func, text
from database import AsyncSessionLocal, engine
from models.triage_model import TriageJob
from models.worker_model import WorkerHeartbeat
from routers.triage import TriageRequest
from routers.triage import _execute_triage_pipeline

from utils.logging_config import setup_structured_logging, job_id_var, worker_id_var, request_id_var, user_id_var
from utils.metrics import metrics_manager

setup_structured_logging(service_name="roadsos-worker")
logger = logging.getLogger("roadsos.worker")

shutdown_event = asyncio.Event()

def signal_handler():
    logger.info("Shutdown signal received (SIGTERM/SIGINT). Initiating graceful shutdown...")
    shutdown_event.set()

async def update_worker_heartbeat(db, worker_id: str, status: str = "active", current_job_id: str = None, inc_completed: bool = False, inc_failed: bool = False):
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        stmt = select(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == worker_id)
        res = await db.execute(stmt)
        record = res.scalars().first()
        if not record:
            record = WorkerHeartbeat(
                worker_id=worker_id,
                status=status,
                started_at=now_utc,
                last_heartbeat=now_utc,
                current_job_id=current_job_id,
                completed_jobs=1 if inc_completed else 0,
                failed_jobs=1 if inc_failed else 0
            )
            db.add(record)
        else:
            record.status = status
            record.last_heartbeat = now_utc
            record.current_job_id = current_job_id
            if inc_completed:
                record.completed_jobs = (record.completed_jobs or 0) + 1
            if inc_failed:
                record.failed_jobs = (record.failed_jobs or 0) + 1
        await db.commit()
    except Exception as e:
        logger.warning(f"Failed to update worker heartbeat for {worker_id}: {e}")
        await db.rollback()

async def worker_loop():
    worker_id = f"worker-{uuid.uuid4()}"
    worker_id_var.set(worker_id)

    logger.info(
        "Worker starting",
        extra={
            "event_name": "worker.started",
            "worker_id": worker_id
        }
    )
    
    is_postgres = engine.dialect.name == "postgresql"
    if is_postgres:
        logger.info("Connected to PostgreSQL. Using true distributed locking (FOR UPDATE SKIP LOCKED).", extra={"event_name": "worker.db.connected"})
    else:
        logger.warning("Connected to SQLite. Using basic sequential locking for test/dev mode.", extra={"event_name": "worker.db.connected"})

    # Register initial heartbeat
    async with AsyncSessionLocal() as db:
        await update_worker_heartbeat(db, worker_id, status="active")

    loop = asyncio.get_running_loop()
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
    except (NotImplementedError, RuntimeError):
        pass

    poll_interval = float(os.getenv("WORKER_POLL_INTERVAL", "2.0"))
    stale_timeout_minutes = int(os.getenv("WORKER_STALE_TIMEOUT_MINUTES", "5"))
    max_attempts = int(os.getenv("WORKER_MAX_ATTEMPTS", "3"))

    while not shutdown_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                timeout_threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=stale_timeout_minutes)
                now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                
                # Emit heartbeat
                await update_worker_heartbeat(db, worker_id, status="active")

                job_id = None
                
                if is_postgres:
                    stmt = text("""
                        UPDATE triage_jobs
                        SET status = 'processing', worker_id = :worker_id, started_at = :now, heartbeat_at = :now
                        WHERE id = (
                            SELECT id FROM triage_jobs
                            WHERE status = 'pending'
                               OR (status = 'processing' AND heartbeat_at < :timeout)
                            ORDER BY created_at ASC
                            FOR UPDATE SKIP LOCKED
                            LIMIT 1
                        )
                        RETURNING id, payload, user_id, request_id, attempt_count
                    """)
                    result = await db.execute(stmt, {
                        "worker_id": worker_id,
                        "now": now_utc,
                        "timeout": timeout_threshold
                    })
                    row = result.fetchone()
                    if row:
                        job_id, payload, user_id, request_id, attempt_count = row
                        await db.commit()
                else:
                    sel_stmt = select(TriageJob).where(
                        (TriageJob.status == "pending") |
                        ((TriageJob.status == "processing") & (TriageJob.heartbeat_at < timeout_threshold))
                    ).order_by(TriageJob.created_at.asc()).limit(1)
                    
                    res = await db.execute(sel_stmt)
                    job = res.scalars().first()
                    
                    if job:
                        job.status = "processing"
                        job.worker_id = worker_id
                        job.started_at = now_utc
                        job.heartbeat_at = now_utc
                        
                        job_id = job.id
                        payload = job.payload
                        user_id = job.user_id
                        request_id = job.request_id
                        attempt_count = job.attempt_count
                        
                        await db.commit()

                if not job_id:
                    await asyncio.sleep(poll_interval)
                    continue
                
                # Set correlation contextvars
                job_id_var.set(job_id)
                if request_id:
                    request_id_var.set(request_id)
                if user_id:
                    user_id_var.set(str(user_id))

                logger.info(
                    "Worker claimed job",
                    extra={
                        "event_name": "worker.job.claimed",
                        "job_id": job_id,
                        "worker_id": worker_id,
                        "request_id": request_id,
                        "user_id": str(user_id) if user_id else None,
                        "attempt_count": attempt_count + 1
                    }
                )
                await update_worker_heartbeat(db, worker_id, status="active", current_job_id=job_id)
                
                try:
                    req = TriageRequest(**payload)
                    result = await _execute_triage_pipeline(
                        req=req,
                        db=db,
                        user_id=user_id,
                        processing_mode="async",
                        job_id=job_id,
                        request_id=request_id
                    )
                    
                    upd_stmt = update(TriageJob).where(TriageJob.id == job_id).values(
                        status="completed",
                        result=result,
                        error=None
                    )
                    await db.execute(upd_stmt)
                    await db.commit()

                    logger.info(
                        "Worker completed job",
                        extra={
                            "event_name": "worker.job.completed",
                            "job_id": job_id,
                            "worker_id": worker_id,
                            "status": "completed"
                        }
                    )
                    metrics_manager.record_worker_job(worker_id, "completed")
                    await update_worker_heartbeat(db, worker_id, status="active", current_job_id=None, inc_completed=True)
                    
                except Exception as e:
                    attempt_count += 1
                    if attempt_count >= max_attempts:
                        new_status = "failed"
                        event_name = "worker.job.failed"
                    else:
                        new_status = "pending"
                        event_name = "worker.job.retry"

                    logger.error(
                        f"Worker job error: {e}",
                        extra={
                            "event_name": event_name,
                            "job_id": job_id,
                            "worker_id": worker_id,
                            "attempt_count": attempt_count,
                            "status": new_status
                        },
                        exc_info=True
                    )
                    metrics_manager.record_worker_job(worker_id, new_status)
                        
                    upd_stmt = update(TriageJob).where(TriageJob.id == job_id).values(
                        status=new_status,
                        attempt_count=attempt_count,
                        error=str(e)
                    )
                    await db.execute(upd_stmt)
                    await db.commit()
                    await update_worker_heartbeat(db, worker_id, status="active", current_job_id=None, inc_failed=True)
                    
        except Exception as e:
            logger.error("Worker loop error", extra={"event_name": "worker.error"}, exc_info=True)
            await asyncio.sleep(5)

    # Mark worker as stopping on exit
    logger.info("Worker exiting cleanly", extra={"event_name": "worker.stopped", "worker_id": worker_id})
    try:
        async with AsyncSessionLocal() as db:
            await update_worker_heartbeat(db, worker_id, status="stopping", current_job_id=None)
    except Exception as e:
        logger.warning(f"Error recording worker shutdown state: {e}")

if __name__ == "__main__":
    asyncio.run(worker_loop())
