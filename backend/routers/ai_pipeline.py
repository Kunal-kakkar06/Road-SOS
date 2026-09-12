"""
routers/ai_pipeline.py
========================
FastAPI router for the AI subsystem health check and worker cluster visibility.

Endpoints:
  GET /api/ai/health
  GET /api/ai/worker-health

Reports operational status without making external API calls or running inference.
"""

from __future__ import annotations

import os
import logging
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger("roadsos.routers.ai_pipeline")

router = APIRouter(prefix="/api/ai", tags=["AI Pipeline"])

APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

@router.get("/health")
async def ai_health():
    """
    Return the health status of all AI pipeline components and application version.
    """
    try:
        from ai.pipeline.orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        health = orchestrator.health_check()
        return {
            "status": "ok",
            "app_version": APP_VERSION,
            "ai_subsystem": "initialized",
            **health,
        }
    except Exception as exc:
        logger.error("[ai_pipeline] health check failed: %s", exc)
        return {
            "status": "degraded",
            "app_version": APP_VERSION,
            "ai_subsystem": "error",
            "error": "AI subsystem failed to initialize. Check server logs.",
        }

@router.get("/worker-health")
async def worker_health():
    """
    Return operational health visibility for the distributed worker system.
    Exposes worker status, last heartbeat timestamp, and current job ID without exposing patient data.
    """
    try:
        from database import AsyncSessionLocal
        from sqlalchemy import text

        stale_threshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=2)
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                text("SELECT worker_id, last_heartbeat, status, current_job_id, completed_jobs, failed_jobs FROM worker_heartbeats WHERE last_heartbeat >= :thresh ORDER BY last_heartbeat DESC"),
                {"thresh": stale_threshold}
            )
            workers = []
            for row in res.fetchall():
                ts = row[1]
                ts_str = ts.isoformat() if hasattr(ts, "isoformat") else (str(ts) if ts else None)
                workers.append({
                    "worker_id": row[0],
                    "last_heartbeat": ts_str,
                    "status": row[2],
                    "job_id": row[3],
                    "completed_jobs": row[4] or 0,
                    "failed_jobs": row[5] or 0
                })
        
        return {
            "status": "healthy" if workers else "idle",
            "app_version": APP_VERSION,
            "active_worker_count": len(workers),
            "workers": workers
        }
    except Exception as exc:
        logger.error("[ai_pipeline] worker health check failed: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "status": "unavailable",
                "app_version": APP_VERSION,
                "error": "Failed to retrieve worker cluster health"
            }
        )
