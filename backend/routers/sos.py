from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from database import get_db
from schemas import SOSTriggerRequest, SOSSyncRequest, SOSResponse
from models.sos_model import SOSEvent
from services.sms_service import send_sos_sms

router = APIRouter(prefix="/api/sos", tags=["SOS"])


# ── POST /api/sos/trigger ─────────────────────────────────────
@router.post("/trigger", response_model=SOSResponse)
async def trigger_sos(
    payload:          SOSTriggerRequest,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    if not payload.contacts:
        raise HTTPException(status_code=400, detail="No emergency contacts configured")

    # 1. Save to DB immediately (async)
    event = SOSEvent(
        event_id        = payload.eventId,
        user_id         = payload.profile.userId or "anonymous",
        latitude        = payload.coords.lat,
        longitude       = payload.coords.lng,
        timestamp       = payload.timestamp,
        medical_profile = payload.profile.model_dump(),
        contacts        = [c.model_dump() for c in payload.contacts],
        was_offline     = False,
    )
    db.add(event)
    await db.commit()

    # 2. Fire SMS in background task
    background_tasks.add_task(
        send_sos_sms,
        contacts  = payload.contacts,
        profile   = payload.profile,
        coords    = payload.coords,
        timestamp = payload.timestamp,
        event_id  = payload.eventId,
        db        = db,
        delayed   = False,
    )

    return SOSResponse(
        success = True,
        eventId = payload.eventId,
        sent    = len(payload.contacts),
        failed  = 0,
        message = "SOS logged. SMS sending in background.",
    )


# ── POST /api/sos/sync ────────────────────────────────────────
@router.post("/sync")
async def sync_sos_queue(
    payload:          SOSSyncRequest,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    if not payload.events:
        return {"results": []}

    results = []

    for ev in payload.events:
        # Idempotent check
        existing_res = await db.execute(select(SOSEvent).filter(SOSEvent.event_id == ev.eventId))
        existing = existing_res.scalars().first()

        if existing and existing.sms_sent:
            results.append({"eventId": ev.eventId, "synced": True, "skipped": True})
            continue

        if not existing:
            record = SOSEvent(
                event_id        = ev.eventId,
                user_id         = ev.profile.userId or "anonymous",
                latitude        = ev.coords.lat,
                longitude       = ev.coords.lng,
                timestamp       = ev.timestamp,
                medical_profile = ev.profile.model_dump(),
                contacts        = [c.model_dump() for c in ev.contacts],
                was_offline     = True,
                synced_at       = datetime.utcnow(),
            )
            db.add(record)
            await db.commit()

        # Send delayed SMS in background
        background_tasks.add_task(
            send_sos_sms,
            contacts  = ev.contacts,
            profile   = ev.profile,
            coords    = ev.coords,
            timestamp = ev.timestamp,
            event_id  = ev.eventId,
            db        = db,
            delayed   = True,
        )

        results.append({"eventId": ev.eventId, "synced": True})

    return {"results": results}


# ── GET /api/sos/log ──────────────────────────────────────────
@router.get("/log")
async def get_sos_log(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SOSEvent).order_by(SOSEvent.created_at.desc()).limit(50))
    events = result.scalars().all()
    return [
        {
            "eventId":    e.event_id,
            "timestamp":  e.timestamp,
            "coords":     {"lat": e.latitude, "lng": e.longitude},
            "smsSent":    e.sms_sent,
            "smsCount":   e.sms_count,
            "wasOffline": e.was_offline,
        }
        for e in events
    ]
