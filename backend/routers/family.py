from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
import asyncio
import json
import uuid

from database import get_db
from models import TrackingSession
from schemas import CreateAlertRequest, LocationUpdateRequest, UpdateStatusRequest
from services.family_sms import send_family_alert_sms
from services.redis_service import get_cached, set_cached

router = APIRouter(prefix="/api/family", tags=["Family Alerts"])

TRACKING_BASE_URL = "http://localhost:5173"  # change to production URL


# ── POST /api/family/alert ────────────────────────────────────
@router.post("/alert")
async def create_alert(
    payload:          CreateAlertRequest,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    session_id = str(uuid.uuid4())[:12]   # short ID for readable URL
    tracking_url = f"{TRACKING_BASE_URL}/track/{session_id}"

    # Create session in DB
    session = TrackingSession(
        session_id        = session_id,
        sos_event_id      = payload.sos_event_id,
        incident_id       = payload.incident_id,
        user_id           = payload.user_id,
        patient_name      = payload.patient_name,
        severity          = payload.severity,
        initial_lat       = payload.latitude,
        initial_lng       = payload.longitude,
        latest_lat        = payload.latitude,
        latest_lng        = payload.longitude,
        contacts_notified = payload.contacts,
        location_updated  = datetime.utcnow(),
        expires_at        = datetime.utcnow() + timedelta(hours=24),
        was_offline       = False,
    )
    db.add(session)
    await db.commit()

    # Cache initial location in Redis/in-memory
    await set_cached(
        f"location:{session_id}",
        json.dumps({
            "lat":       payload.latitude,
            "lng":       payload.longitude,
            "ts":        datetime.utcnow().isoformat(),
            "severity":  payload.severity,
            "name":      payload.patient_name,
        }),
        ttl = 86400,  # 24 hours
    )

    # Helper function to execute background SMS with a new DB session
    def trigger_sms():
        async def run_sms():
            async with db.bind.connect() as conn:
                # BackgroundTasks can trigger async execution directly
                await send_family_alert_sms(
                    contacts     = payload.contacts,
                    patient_name = payload.patient_name,
                    severity     = payload.severity,
                    latitude     = payload.latitude,
                    longitude    = payload.longitude,
                    tracking_url = tracking_url,
                    session_id   = session_id,
                    db           = db,
                    delayed      = False,
                )
        asyncio.create_task(run_sms())

    background_tasks.add_task(trigger_sms)

    return {
        "session_id":   session_id,
        "tracking_url": tracking_url,
        "contacts":     len(payload.contacts),
        "status":       "alert_sent",
    }


# ── POST /api/family/sync-offline ─────────────────────────────
@router.post("/sync-offline")
async def sync_offline_alerts(
    payload:          dict,
    background_tasks: BackgroundTasks,
    db:               AsyncSession = Depends(get_db),
):
    alerts  = payload.get("alerts", [])
    results = []

    for alert in alerts:
        session_id   = str(uuid.uuid4())[:12]
        tracking_url = f"{TRACKING_BASE_URL}/track/{session_id}"

        session = TrackingSession(
            session_id        = session_id,
            sos_event_id      = alert.get("sos_event_id"),
            user_id           = alert.get("user_id", "anonymous"),
            patient_name      = alert.get("patient_name"),
            severity          = alert.get("severity", "P2"),
            initial_lat       = alert.get("latitude", 0),
            initial_lng       = alert.get("longitude", 0),
            latest_lat        = alert.get("latitude", 0),
            latest_lng        = alert.get("longitude", 0),
            contacts_notified = alert.get("contacts", []),
            location_updated  = datetime.utcnow(),
            expires_at        = datetime.utcnow() + timedelta(hours=24),
            was_offline       = True,
        )
        db.add(session)
        await db.commit()

        # Cache location
        await set_cached(
            f"location:{session_id}",
            json.dumps({
                "lat": alert.get("latitude", 0),
                "lng": alert.get("longitude", 0),
                "ts": datetime.utcnow().isoformat(),
                "severity": alert.get("severity", "P2"),
                "name": alert.get("patient_name")
            }),
            ttl=86400,
        )

        # Trigger background SMS
        def trigger_sms_offline():
            async def run_sms_offline():
                await send_family_alert_sms(
                    contacts     = alert.get("contacts", []),
                    patient_name = alert.get("patient_name"),
                    severity     = alert.get("severity", "P2"),
                    latitude     = alert.get("latitude", 0),
                    longitude    = alert.get("longitude", 0),
                    tracking_url = tracking_url,
                    session_id   = session_id,
                    db           = db,
                    delayed      = True,
                )
            asyncio.create_task(run_sms_offline())

        background_tasks.add_task(trigger_sms_offline)
        results.append({"session_id": session_id, "synced": True})

    return {"results": results}


# ── POST /api/family/location ─────────────────────────────────
@router.post("/location")
async def update_location(
    payload: LocationUpdateRequest,
    db:      AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrackingSession).filter(TrackingSession.session_id == payload.session_id))
    session = result.scalars().first()
    if not session or not session.is_active:
        raise HTTPException(404, "Session not found or expired")

    # Update DB
    session.latest_lat      = payload.latitude
    session.latest_lng      = payload.longitude
    session.location_updated= datetime.utcnow()
    await db.commit()

    # Update cache
    await set_cached(
        f"location:{payload.session_id}",
        json.dumps({
            "lat":      payload.latitude,
            "lng":      payload.longitude,
            "ts":       datetime.utcnow().isoformat(),
            "severity": session.severity,
            "name":     session.patient_name,
        }),
        ttl=86400,
    )
    return {"updated": True}


# ── PATCH /api/family/session/{id}/status ────────────────────
@router.patch("/session/{session_id}/status")
async def update_session_status(
    session_id: str,
    payload:    UpdateStatusRequest,
    db:         AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TrackingSession).filter(TrackingSession.session_id == session_id))
    session = result.scalars().first()
    if not session:
        raise HTTPException(404, "Session not found")

    if payload.hospital_name is not None:  session.hospital_name  = payload.hospital_name
    if payload.ambulance_name is not None: session.ambulance_name = payload.ambulance_name
    if payload.severity is not None:       session.severity       = payload.severity
    await db.commit()
    return {"updated": True}


# ── GET /api/family/session/{id} ─────────────────────────────
@router.get("/session/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    if session_id == "demo-session-id":
        return {
            "session_id":    "demo-session-id",
            "patient_name":  "Arjun Kumar",
            "severity":      "P2",
            "hospital_name": "Manipal Hospital",
            "ambulance_name":"CATS Unit 4",
            "is_active":     True,
            "was_offline":   False,
            "sms_sent":      True,
            "location":      {"lat": 12.9716, "lng": 77.5946},
            "created_at":    str(datetime.utcnow()),
            "expires_at":    str(datetime.utcnow() + timedelta(hours=24)),
        }

    result = await db.execute(select(TrackingSession).filter(TrackingSession.session_id == session_id))
    session = result.scalars().first()
    if not session:
        raise HTTPException(404, "Tracking session not found")

    cached = await get_cached(f"location:{session_id}")
    location = json.loads(cached) if cached else {
        "lat": session.latest_lat, "lng": session.latest_lng
    }

    return {
        "session_id":    session_id,
        "patient_name":  session.patient_name,
        "severity":      session.severity,
        "hospital_name": session.hospital_name,
        "ambulance_name":session.ambulance_name,
        "is_active":     session.is_active,
        "was_offline":   session.was_offline,
        "sms_sent":      session.sms_sent,
        "location":      location,
        "created_at":    str(session.created_at),
        "expires_at":    str(session.expires_at),
    }


# ── GET /api/family/track/{session_id} ───────────────────────
@router.get("/track/{session_id}")
async def track_location(session_id: str, db: AsyncSession = Depends(get_db)):
    if session_id == "demo-session-id":
        async def demo_stream():
            import random
            lat, lng = 12.9716, 77.5946
            while True:
                lat += random.uniform(-0.0003, 0.0003)
                lng += random.uniform(-0.0003, 0.0003)
                payload_str = json.dumps({
                    'lat': lat, 'lng': lng, 
                    'ts': datetime.utcnow().isoformat(),
                    'severity': 'P2', 'name': 'Arjun Kumar',
                    'session_id': 'demo-session-id',
                    'hospital_name': 'Manipal Hospital',
                    'ambulance_name': 'CATS Unit 4'
                })
                yield f"data: {payload_str}\n\n"
                await asyncio.sleep(5)
        return StreamingResponse(
            demo_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control":               "no-cache",
                "X-Accel-Buffering":           "no",
                "Access-Control-Allow-Origin": "*",
            },
        )

    result = await db.execute(select(TrackingSession).filter(TrackingSession.session_id == session_id))
    session = result.scalars().first()
    if not session:
        raise HTTPException(404, "Session not found")

    async def location_stream():
        from database import AsyncSessionLocal
        last_sent = None
        while True:
            async with AsyncSessionLocal() as transient_session:
                result_session = await transient_session.execute(select(TrackingSession).filter(TrackingSession.session_id == session_id))
                session_obj = result_session.scalars().first()
                
                if not session_obj or not session_obj.is_active or (session_obj.expires_at and datetime.utcnow() > session_obj.expires_at):
                    yield f"data: {json.dumps({'done': True, 'reason': 'session_ended'})}\n\n"
                    break

                # Read latest position from cache
                cached = await get_cached(f"location:{session_id}")
                if cached and cached != last_sent:
                    last_sent = cached
                    data = json.loads(cached)
                    data.update({
                        "session_id":    session_id,
                        "hospital_name": session_obj.hospital_name,
                        "ambulance_name":session_obj.ambulance_name,
                    })
                    yield f"data: {json.dumps(data)}\n\n"

            await asyncio.sleep(5)

    return StreamingResponse(
        location_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ── DELETE /api/family/session/{id} ──────────────────────────
@router.delete("/session/{session_id}")
async def close_session(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrackingSession).filter(TrackingSession.session_id == session_id))
    session = result.scalars().first()
    if session:
        session.is_active = False
        await db.commit()
    return {"closed": True}
