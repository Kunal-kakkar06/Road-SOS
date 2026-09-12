import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.triage_model import TriageJob

logger = logging.getLogger("roadsos.triage_job_manager")

MAX_CONCURRENT_JOBS_PER_USER = 5

async def create_job(user_id: str, db: AsyncSession, request_id: str, payload: dict) -> str:
    """
    Create a new pending job and return its cryptographically safe UUID.
    Enforces per-user concurrency limits with transaction-level locking to prevent race conditions.
    """
    from sqlalchemy import text
    bind = db.bind or (await db.get_bind())
    if bind and bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:uid))"), {"uid": str(user_id)})

    # Check concurrent limits
    stmt = select(func.count()).select_from(TriageJob).where(
        TriageJob.user_id == user_id,
        TriageJob.status.in_(["pending", "processing"])
    )
    result = await db.execute(stmt)
    active_jobs = result.scalar()
    
    if active_jobs >= MAX_CONCURRENT_JOBS_PER_USER:
        from fastapi import HTTPException
        logger.warning(f"User {user_id} exceeded max concurrent async jobs.")
        raise HTTPException(status_code=429, detail="Too many concurrent triage requests. Please wait for them to finish.")
    
    job_id = str(uuid.uuid4())
    new_job = TriageJob(
        id=job_id,
        user_id=user_id,
        status="pending",
        request_id=request_id,
        payload=payload
    )
    
    db.add(new_job)
    await db.commit()
    
    logger.info(f"Created triage job {job_id} for user {user_id}")
    return job_id

async def get_job(job_id: str, user_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """
    Retrieve a job by ID, ensuring the authenticated user owns it.
    Returns None if the job does not exist or belongs to another user.
    """
    stmt = select(TriageJob).where(TriageJob.id == job_id)
    result = await db.execute(stmt)
    job = result.scalars().first()
    
    if not job:
        return None
    if job.user_id != user_id:
        logger.warning(f"Unauthorized access attempt to job {job_id} by user {user_id}")
        return None
        
    return {
        "job_id": job.id,
        "user_id": job.user_id,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "result": job.result,
        "error": job.error
    }

async def update_job(job_id: str, status: str, db: AsyncSession, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
    """
    Update job status and optional result or error.
    """
    stmt = select(TriageJob).where(TriageJob.id == job_id)
    res = await db.execute(stmt)
    job = res.scalars().first()
    
    if not job:
        logger.error(f"Cannot update unknown job {job_id}")
        return

    job.status = status
    if result is not None:
        job.result = result
    if error is not None:
        job.error = error
        
    await db.commit()
    logger.info(f"Job {job_id} updated to status: {status}")

async def cleanup_old_terminal_jobs(db: AsyncSession, retention_days: int = 30) -> int:
    """
    Deletes terminal jobs ('completed', 'failed') older than retention_days.
    Strictly protects TriageEvent audit logs and active 'pending'/'processing' jobs.
    Returns the number of deleted terminal jobs.
    """
    from datetime import timedelta
    from sqlalchemy import delete
    
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=retention_days)
    
    stmt = delete(TriageJob).where(
        TriageJob.status.in_(["completed", "failed"]),
        TriageJob.created_at < cutoff
    )
    result = await db.execute(stmt)
    await db.commit()
    deleted_count = result.rowcount or 0
    logger.info(f"Cleaned up {deleted_count} terminal triage jobs older than {retention_days} days.")
    return deleted_count
