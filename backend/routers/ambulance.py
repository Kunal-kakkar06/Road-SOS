from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import asyncio, json, uuid, math

from database import get_db
from models.ambulance_provider import AmbulanceProvider
from models.dispatch_event import DispatchEvent
from services.maps_service import get_eta_and_distance
from services.ambulance_sms import send_dispatch_sms
from services.redis_service import get_cached, set_cached

router = APIRouter(prefix="/api/ambulance", tags=["Ambulance"])


# ── Geospatial Haversine Fallback ────────────────────────────

def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculates physical distance in kilometers using the Haversine mathematical equation."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


# ── Pydantic Schemas ──────────────────────────────────────────

class DispatchRequest(BaseModel):
    patient_lat:     float
    patient_lng:     float
    patient_user_id: Optional[str] = "anonymous"
    sos_event_id:    Optional[str]   = None
    severity:        Optional[str]   = "P2"
    blood_type:      Optional[str]   = None


class LocationUpdate(BaseModel):
    provider_id: str
    lat:         float
    lng:         float


class StatusUpdate(BaseModel):
    status: str   # en_route / arrived / completed / cancelled


# ── POST /api/ambulance/nearest ──────────────────────────────
@router.post("/nearest")
async def find_nearest(
    lat:      float = Query(...),
    lng:      float = Query(...),
    type:     Optional[str] = Query(None),
    db:       AsyncSession = Depends(get_db),
):
    # Sanitize client coordinates if they are outside of Bengaluru to prevent extreme distances/ETAs
    if haversine_distance(lat, lng, 12.9716, 77.5946) > 100.0:
        lat, lng = 12.9716, 77.5946

    cache_key = f"ambulance_nearest:{round(lat,3)}:{round(lng,3)}:{type}"
    cached = await get_cached(cache_key)
    if cached:
        return json.loads(cached)

    # 1. Fetch available verified providers
    result = await db.execute(select(AmbulanceProvider).filter(
        AmbulanceProvider.is_verified == True,
        AmbulanceProvider.is_available == True,
        AmbulanceProvider.is_active == True
    ))
    providers_raw = result.scalars().all()

    # 2. Filter by type
    if type:
        providers_raw = [p for p in providers_raw if p.type == type]

    # 3. Calculate Haversine distances
    providers = []
    for row in providers_raw:
        dist_km = haversine_distance(lat, lng, row.latitude, row.longitude)
        
        # Relaxed bounds filter for sandbox demo compatibility
        if dist_km > 100000.0:
            continue

        eta_data = await get_eta_and_distance(
            origin_lat=lat, origin_lng=lng,
            dest_lat=row.latitude, dest_lng=row.longitude,
        )

        providers.append({
            "id":            str(row.id),
            "name":          row.name,
            "operator_name": row.operator_name,
            "phone":         row.phone,
            "vehicle_number":row.vehicle_number,
            "type":          row.type,
            "distance_km":   round(dist_km, 1),
            "eta_minutes":   eta_data.get("duration_minutes") or max(3, round(dist_km * 2.0)),
            "eta_text":      eta_data.get("duration_text") or f"{max(3, round(dist_km * 2.0))} mins",
            "is_verified":   row.is_verified,
            "lat":           row.latitude,
            "lng":           row.longitude,
        })

    # Sort nearest
    providers.sort(key=lambda x: x["distance_km"])
    providers = providers[:5]

    response = {"providers": providers}
    await set_cached(cache_key, json.dumps(response), ttl=30)
    return response


# ── POST /api/ambulance/dispatch ──────────────────────────────
@router.post("/dispatch")
async def dispatch_ambulance(
    payload: DispatchRequest,
    db:      AsyncSession = Depends(get_db),
):
    # Sanitize client coordinates if they are outside of Bengaluru to prevent extreme distances/ETAs
    if haversine_distance(payload.patient_lat, payload.patient_lng, 12.9716, 77.5946) > 100.0:
        payload.patient_lat = 12.9716
        payload.patient_lng = 77.5946

    # 1. Find nearest verified unit
    result = await db.execute(select(AmbulanceProvider).filter(
        AmbulanceProvider.is_verified == True,
        AmbulanceProvider.is_available == True,
        AmbulanceProvider.is_active == True
    ))
    providers_raw = result.scalars().all()

    if not providers_raw:
        raise HTTPException(status_code=404, detail="No ambulance available")

    # Compute distances
    candidates = []
    for p in providers_raw:
        dist = haversine_distance(payload.patient_lat, payload.patient_lng, p.latitude, p.longitude)
        if dist <= 100000.0:
            candidates.append((dist, p))

    if not candidates:
        raise HTTPException(status_code=404, detail="No ambulance available")

    candidates.sort(key=lambda x: x[0])
    nearest_dist, provider = candidates[0]


    # 2. Get ETA from Google Maps
    eta_data = await get_eta_and_distance(
        origin_lat=provider.latitude,
        origin_lng=provider.longitude,
        dest_lat=payload.patient_lat,
        dest_lng=payload.patient_lng,
    )

    # 3. Create dispatch event
    dispatch_id = str(uuid.uuid4())
    event = DispatchEvent(
        dispatch_id      = dispatch_id,
        sos_event_id     = payload.sos_event_id,
        provider_id      = str(provider.id),
        patient_lat      = payload.patient_lat,
        patient_lng      = payload.patient_lng,
        patient_user_id  = payload.patient_user_id,
        eta_minutes      = eta_data.get("duration_minutes") or max(3, round(nearest_dist * 2.0)),
        distance_km      = eta_data.get("distance_km") or round(nearest_dist, 1),
        route_url        = eta_data.get("route_url"),
        status           = "dispatched",
    )
    db.add(event)

    # 4. Mark provider as unavailable
    provider.is_available = False
    await db.commit()

    # 5. Send SMS to driver
    sms_sent = await send_dispatch_sms(
        driver_phone     = provider.phone,
        driver_name      = provider.operator_name,
        patient_lat      = payload.patient_lat,
        patient_lng      = payload.patient_lng,
        eta_minutes      = event.eta_minutes,
        dispatch_id      = dispatch_id,
    )

    # Update SMS sent status
    event.driver_sms_sent = sms_sent
    await db.commit()

    return {
        "dispatch_id":    dispatch_id,
        "provider_id":    str(provider.id),
        "provider_name":  provider.name,
        "operator_name":  provider.operator_name,
        "driver_phone":   provider.phone,
        "vehicle_number": provider.vehicle_number,
        "type":           provider.type,
        "eta_minutes":    event.eta_minutes,
        "eta_text":       f"{event.eta_minutes} mins",
        "distance_km":    event.distance_km,
        "route_url":      event.route_url,
        "driver_sms_sent":sms_sent,
        "status":         "dispatched",
    }


# ── POST /api/ambulance/location ─────────────────────────────
@router.post("/location")
async def update_driver_location(
    payload: LocationUpdate,
    db:      AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AmbulanceProvider).filter(AmbulanceProvider.id == payload.provider_id))
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(404, "Provider not found")

    provider.latitude         = payload.lat
    provider.longitude        = payload.lng
    provider.location_updated = datetime.utcnow()
    await db.commit()

    # Cache latest position for SSE stream
    await set_cached(
        f"driver_location:{payload.provider_id}",
        json.dumps({"lat": payload.lat, "lng": payload.lng,
                    "ts": datetime.utcnow().isoformat()}),
        ttl=30,
    )
    return {"updated": True}


# ── PATCH /api/ambulance/dispatch/{id}/status ─────────────────
@router.patch("/dispatch/{dispatch_id}/status")
async def update_dispatch_status(
    dispatch_id: str,
    payload:     StatusUpdate,
    db:          AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DispatchEvent).filter(DispatchEvent.dispatch_id == dispatch_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(404, "Dispatch not found")

    event.status = payload.status
    if payload.status == "arrived":
        event.arrived_at = datetime.utcnow()
    elif payload.status in ["completed", "cancelled"]:
        event.completed_at = datetime.utcnow()
        # Free up the ambulance
        res_provider = await db.execute(select(AmbulanceProvider).filter(AmbulanceProvider.id == event.provider_id))
        provider = res_provider.scalars().first()
        if provider:
            provider.is_available = True
    await db.commit()
    return {"dispatch_id": dispatch_id, "status": payload.status}


# ── GET /api/ambulance/dispatch/{id} ─────────────────────────
@router.get("/dispatch/{dispatch_id}")
async def get_dispatch(dispatch_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DispatchEvent).filter(DispatchEvent.dispatch_id == dispatch_id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(404, "Dispatch not found")

    loc_cached = await get_cached(f"driver_location:{event.provider_id}")
    driver_location = json.loads(loc_cached) if loc_cached else None

    return {
        "dispatch_id":    event.dispatch_id,
        "provider_id":    event.provider_id,
        "status":         event.status,
        "eta_minutes":    event.eta_minutes,
        "distance_km":    event.distance_km,
        "route_url":      event.route_url,
        "driver_location":driver_location,
        "dispatched_at":  str(event.dispatched_at),
        "arrived_at":     str(event.arrived_at) if event.arrived_at else None,
    }


# ── GET /api/ambulance/providers ─────────────────────────────
@router.get("/providers")
async def list_providers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AmbulanceProvider).filter(AmbulanceProvider.is_verified == True))
    providers = result.scalars().all()
    return [
        {
            "id": str(p.id), "name": p.name, "type": p.type,
            "lat": p.latitude, "lng": p.longitude,
            "is_available": p.is_available,
            "vehicle_number": p.vehicle_number,
        }
        for p in providers
    ]


# ── GET /api/ambulance/track/{dispatch_id} (SSE) ──────────────
@router.get("/track/{dispatch_id}")
async def track_ambulance(dispatch_id: str, db: AsyncSession = Depends(get_db)):
    """
    SSE tracking stream. Driver updates positions dynamically, 
    and this pushes coordinates to patient client every 5s.
    """
    result = await db.execute(select(DispatchEvent).filter(DispatchEvent.dispatch_id == dispatch_id))
    event = result.scalars().first()
    if not event:
        return {"error": "Dispatch not found"}

    provider_id = event.provider_id

    async def location_stream():
        last_location = None
        while True:
            cached = await get_cached(f"driver_location:{provider_id}")

            if cached:
                location = json.loads(cached)
                if location != last_location:
                    last_location = location

                    # Fresh query to monitor dispatch status changes
                    res_dispatch = await db.execute(select(DispatchEvent).filter(DispatchEvent.dispatch_id == dispatch_id))
                    dispatch = res_dispatch.scalars().first()

                    payload = {
                        "dispatch_id": dispatch_id,
                        "driver_lat":  location["lat"],
                        "driver_lng":  location["lng"],
                        "timestamp":   location["ts"],
                        "status":      dispatch.status if dispatch else "unknown",
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

            res_dispatch = await db.execute(select(DispatchEvent).filter(DispatchEvent.dispatch_id == dispatch_id))
            dispatch = res_dispatch.scalars().first()
            if dispatch and dispatch.status in ["completed", "cancelled"]:
                yield f"data: {json.dumps({'status': dispatch.status, 'done': True})}\n\n"
                break

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
