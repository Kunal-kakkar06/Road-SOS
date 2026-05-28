from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
from typing import Optional, List
import asyncio
import json
import os
from datetime import datetime

from database import get_db
from models.hospital_model import Hospital
from services.maps_service import get_eta_and_distance, haversine_km
from services.redis_service import get_cached, set_cached

router = APIRouter(prefix="/api/hospitals", tags=["Hospitals"])


# ── Scoring Algorithm ─────────────────────────────────────────
def compute_score(
    distance_km: float,
    eta_minutes: int,
    trauma_beds: int,
    icu_beds: int,
    blood_match: Optional[bool],
    severity: str,
) -> float:
    eta_weight = 3.0 if severity in ["P1", "P2"] else 1.5
    distance_weight = 1.0
    beds_weight = 2.0

    score = (eta_minutes * eta_weight)
    score += (distance_km * distance_weight)
    score -= (trauma_beds * beds_weight)
    score -= (icu_beds * 1.5)
    if blood_match is True:
        score -= 20
    if blood_match is False:
        score += 10
    return round(score, 1)


# ── POST /api/hospitals/nearest ───────────────────────────────
@router.post("/nearest")
async def get_nearest_hospitals(
    lat: float = Query(..., description="User latitude"),
    lng: float = Query(..., description="User longitude"),
    blood_type: Optional[str] = Query(None, description="Patient blood type e.g. B+"),
    severity: Optional[str] = Query("P2", description="Severity: P1/P2/P3/P4"),
    db: AsyncSession = Depends(get_db),
):
    # Sanitize client coordinates if they are outside of Bengaluru to prevent extreme distances/ETAs
    if haversine_km(lat, lng, 12.9716, 77.5946) > 100.0:
        lat, lng = 12.9716, 77.5946

    # 1. Check Cache
    cache_key = f"hospitals:{round(lat, 3)}:{round(lng, 3)}:{blood_type}:{severity}"
    cached = await get_cached(cache_key)
    if cached:
        return json.loads(cached)

    # 2. Query hospitals from database
    is_sqlite = "sqlite" in os.getenv("DATABASE_URL", "")
    if is_sqlite:
        # Standard database query fallback
        stmt = select(Hospital).filter(Hospital.is_active == True)
        result = await db.execute(stmt)
        all_hospitals = result.scalars().all()

        hospitals_with_distance = []
        for h in all_hospitals:
            dist = haversine_km(lat, lng, h.latitude, h.longitude)
            h_dict = {
                "id": str(h.id),
                "name": h.name,
                "address": h.address,
                "phone": h.phone,
                "type": h.type,
                "latitude": h.latitude,
                "longitude": h.longitude,
                "trauma_beds_available": h.trauma_beds_available,
                "icu_beds_available": h.icu_beds_available,
                "general_beds_available": h.general_beds_available,
                "blood_bank": h.blood_bank,
                "blood_types_available": h.blood_types_available,
                "has_trauma_center": h.has_trauma_center,
                "has_cath_lab": h.has_cath_lab,
                "has_neuro_unit": h.has_neuro_unit,
                "distance_km": dist
            }
            hospitals_with_distance.append(h_dict)
        hospitals_with_distance.sort(key=lambda h: h["distance_km"])
        nearby = hospitals_with_distance
    else:
        # PostgreSQL/PostGIS query
        query = text("""
            SELECT
                h.id, h.name, h.address, h.phone, h.type, h.latitude, h.longitude,
                h.trauma_beds_available, h.icu_beds_available, h.general_beds_available,
                h.blood_bank, h.blood_types_available, h.has_trauma_center, h.has_cath_lab,
                h.has_neuro_unit,
                ST_Distance(
                    h.location::geography,
                    ST_MakePoint(:lng, :lat)::geography
                ) AS distance_meters
            FROM hospitals h
            WHERE h.is_active = true
            ORDER BY distance_meters ASC
            LIMIT 10
        """)
        result = await db.execute(query, {"lat": lat, "lng": lng})
        nearby = []
        for row in result.mappings().all():
            nearby.append({
                "id": str(row["id"]),
                "name": row["name"],
                "address": row["address"],
                "phone": row["phone"],
                "type": row["type"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "trauma_beds_available": row["trauma_beds_available"],
                "icu_beds_available": row["icu_beds_available"],
                "general_beds_available": row["general_beds_available"],
                "blood_bank": row["blood_bank"],
                "blood_types_available": row["blood_types_available"],
                "has_trauma_center": row["has_trauma_center"],
                "has_cath_lab": row["has_cath_lab"],
                "has_neuro_unit": row["has_neuro_unit"],
                "distance_km": row["distance_meters"] / 1000.0
            })

    if not nearby:
        return {"hospitals": [], "message": "No hospitals found within 30km"}

    # 3. Fetch traffic directions and rank them
    hospitals = []
    for h in nearby[:5]:
        eta_data = await get_eta_and_distance(
            origin_lat=lat, origin_lng=lng,
            dest_lat=h["latitude"], dest_lng=h["longitude"],
        )

        blood_match = None
        if blood_type:
            blood_match = blood_type in (h["blood_types_available"] or [])

        score = compute_score(
            distance_km=h["distance_km"],
            eta_minutes=eta_data.get("duration_minutes", 999),
            trauma_beds=h["trauma_beds_available"],
            icu_beds=h["icu_beds_available"],
            blood_match=blood_match,
            severity=severity or "P2",
        )

        hospitals.append({
            "id": h["id"],
            "name": h["name"],
            "address": h["address"],
            "phone": h["phone"],
            "type": h["type"],
            "latitude": h["latitude"],
            "longitude": h["longitude"],
            "distance_km": round(h["distance_km"], 1),
            "eta_minutes": eta_data.get("duration_minutes"),
            "eta_text": eta_data.get("duration_text"),
            "route_url": eta_data.get("route_url"),
            "trauma_beds": h["trauma_beds_available"],
            "icu_beds": h["icu_beds_available"],
            "general_beds": h["general_beds_available"],
            "blood_bank": h["blood_bank"],
            "blood_match": blood_match,
            "blood_types": h["blood_types_available"] or [],
            "has_trauma": h["has_trauma_center"],
            "has_cath_lab": h["has_cath_lab"],
            "has_neuro": h["has_neuro_unit"],
            "score": score,
        })

    hospitals.sort(key=lambda h: h["score"])
    response = {"hospitals": hospitals[:3]}

    # Cache for 5 minutes
    await set_cached(cache_key, json.dumps(response), ttl=300)
    return response


# ── GET /api/hospitals ────────────────────────────────────────
@router.get("/")
async def list_hospitals(db: AsyncSession = Depends(get_db)):
    stmt = select(Hospital).filter(Hospital.is_active == True)
    result = await db.execute(stmt)
    hospitals = result.scalars().all()
    return [
        {
            "id": str(h.id),
            "name": h.name,
            "lat": h.latitude,
            "lng": h.longitude,
            "type": h.type,
            "trauma_beds": h.trauma_beds_available,
            "icu_beds": h.icu_beds_available,
        }
        for h in hospitals
    ]


# ── GET /api/hospitals/{hospital_id}/beds ─────────────────────
@router.get("/{hospital_id}/beds")
async def get_bed_status(hospital_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Hospital).filter(Hospital.id == hospital_id)
    result = await db.execute(stmt)
    h = result.scalar_one_or_none()
    if not h:
        return {"error": "Hospital not found"}
    return {
        "hospital_id": hospital_id,
        "trauma_beds": h.trauma_beds_available,
        "icu_beds": h.icu_beds_available,
        "general_beds": h.general_beds_available,
        "blood_bank": h.blood_bank,
        "blood_types": h.blood_types_available or [],
        "updated_at": str(h.beds_updated_at),
    }


# ── PATCH /api/hospitals/{hospital_id}/beds ───────────────────
@router.patch("/{hospital_id}/beds")
async def update_bed_status(
    hospital_id: str,
    trauma_beds: Optional[int] = Query(None),
    icu_beds: Optional[int] = Query(None),
    general_beds: Optional[int] = Query(None),
    blood_types: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Hospital).filter(Hospital.id == hospital_id)
    result = await db.execute(stmt)
    h = result.scalar_one_or_none()
    if not h:
        return {"error": "Hospital not found"}

    if trauma_beds is not None:
        h.trauma_beds_available = trauma_beds
    if icu_beds is not None:
        h.icu_beds_available = icu_beds
    if general_beds is not None:
        h.general_beds_available = general_beds
    if blood_types is not None:
        h.blood_types_available = blood_types

    h.beds_updated_at = datetime.utcnow()
    await db.commit()

    # Invalidate cache
    await set_cached(f"beds:{hospital_id}", None, ttl=1)
    return {"updated": True}


# ── GET /api/hospitals/live/{hospital_id} — SSE ───────────────
@router.get("/live/{hospital_id}")
async def live_bed_updates(hospital_id: str, db: AsyncSession = Depends(get_db)):
    async def event_generator():
        while True:
            # Create a separate transaction scope inside generator
            stmt = select(Hospital).filter(Hospital.id == hospital_id)
            result = await db.execute(stmt)
            # Expire cache to read fresh state from SQLite db
            db.expire_all()
            h = result.scalar_one_or_none()
            if h:
                data = {
                    "hospital_id": hospital_id,
                    "trauma_beds": h.trauma_beds_available,
                    "icu_beds": h.icu_beds_available,
                    "general_beds": h.general_beds_available,
                    "blood_types": h.blood_types_available or [],
                    "timestamp": str(h.beds_updated_at),
                }
                yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(30)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )
