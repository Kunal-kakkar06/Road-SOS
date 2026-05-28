from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from schemas import CrashAnalyseRequest, ManualCrashRequest, CrashSOSUpdate
from models.crash_model import CrashEvent
from services.crash_ml import predict_crash

router = APIRouter(prefix="/api/crash", tags=["Crash"])


@router.post("/analyse")
async def analyse(payload: CrashAnalyseRequest, db: AsyncSession = Depends(get_db)):
    result = predict_crash(
        payload.peak_acceleration, payload.delta_v, payload.jerk,
        payload.rotation_rate, payload.impact_duration_ms, payload.pre_event_accel
    )
    db.add(CrashEvent(
        event_id=payload.eventId, user_id=payload.userId or "anon",
        latitude=payload.latitude, longitude=payload.longitude,
        timestamp=payload.timestamp,
        crash_probability=result['crash_probability'],
        severity=result['severity'], severity_label=result['severity_label'],
        sensor_data={"peak_accel": payload.peak_acceleration,
                     "delta_v": payload.delta_v, "jerk": payload.jerk},
        was_manual=False,
    ))
    await db.commit()
    return {"eventId": payload.eventId, **result}


@router.post("/manual")
async def manual(payload: ManualCrashRequest, db: AsyncSession = Depends(get_db)):
    # Estimate sensor features from manual answers
    peak = payload.vehicle_speed * 0.3 * (2.5 if payload.airbag_deployed else 1)
    dv   = payload.vehicle_speed * 0.4 * (2.0 if payload.airbag_deployed else 1)
    result = predict_crash(peak, dv, peak*1.5, 30.0, 200.0, 3.0)
    
    # Cannot move = upgrade to at least P2
    if not payload.can_move and result['severity'] in ['P3','P4']:
        result['severity']       = 'P2'
        result['severity_label'] = 'Serious — person unable to move'
        
    db.add(CrashEvent(
        event_id=payload.eventId, user_id=payload.userId or "anon",
        latitude=payload.latitude, longitude=payload.longitude,
        timestamp=payload.timestamp,
        crash_probability=result['crash_probability'],
        severity=result['severity'], severity_label=result['severity_label'],
        was_manual=True,
    ))
    await db.commit()
    return {"eventId": payload.eventId, "isCrash": True, **result}


@router.patch("/sos-status")
async def sos_status(payload: CrashSOSUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CrashEvent).filter(CrashEvent.event_id == payload.eventId))
    ev = result.scalars().first()
    if not ev: raise HTTPException(404, "Event not found")
    ev.sos_triggered = payload.sos_triggered
    ev.cancelled     = payload.cancelled
    await db.commit()
    return {"updated": True}


@router.get("/log")
async def log(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CrashEvent).order_by(CrashEvent.created_at.desc()).limit(50))
    evs = result.scalars().all()
    return [{"eventId": e.event_id, "severity": e.severity,
             "probability": e.crash_probability, "wasManual": e.was_manual,
             "sosFired": e.sos_triggered, "cancelled": e.cancelled} for e in evs]
