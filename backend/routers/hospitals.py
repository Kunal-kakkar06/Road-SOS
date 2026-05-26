"""
Hospital Routing & Bed Availability API
========================================
Endpoints:
  POST /api/hospitals/nearest   — Find top 3 hospitals ranked by composite score
  GET  /api/hospitals           — List all hospitals
  GET  /api/hospitals/{id}/beds — Get current bed counts
  PATCH /api/hospitals/{id}/beds — Update bed counts (mock staff dashboard)
  GET  /api/hospitals/live/{id} — SSE live bed count stream (every 30s)
"""
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
import asyncio
import json

from data.hospitals_data import get_all_hospitals, get_hospital_by_id, update_hospital_beds
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
    """
    Lower score = better hospital choice.
    Weights shift based on severity:
      P1/P2 (critical): ETA weighted 3x — get there FAST
      P3/P4 (moderate): ETA weighted 1.5x — can travel further for better facility
    """
    eta_weight = 3.0 if severity in ["P1", "P2"] else 1.5
    distance_weight = 1.0
    beds_weight = 2.0

    score = (eta_minutes * eta_weight)
    score += (distance_km * distance_weight)
    score -= (trauma_beds * beds_weight)
    score -= (icu_beds * 1.5)
    if blood_match is True:
        score -= 20  # big bonus for blood type match
    if blood_match is False:
        score += 10  # penalty if no match
    return round(score, 1)


# ── POST /api/hospitals/nearest ───────────────────────────────
@router.post("/nearest")
async def get_nearest_hospitals(
    lat: float = Query(..., description="User latitude"),
    lng: float = Query(..., description="User longitude"),
    blood_type: Optional[str] = Query(None, description="Patient blood type e.g. B+"),
    severity: Optional[str] = Query("P2", description="Severity: P1/P2/P3/P4"),
):
    """
    Find top 3 hospitals ranked by composite score.
    Uses haversine distance + Google Maps ETA (or fallback).
    Results cached for 5 minutes.
    """
    # 1. Check cache
    cache_key = f"hospitals:{round(lat, 3)}:{round(lng, 3)}:{blood_type}:{severity}"
    cached = await get_cached(cache_key)
    if cached:
        return json.loads(cached)

    # 2. Get all hospitals and compute distances
    all_hospitals = get_all_hospitals()
    for h in all_hospitals:
        h["distance_km"] = haversine_km(lat, lng, h["latitude"], h["longitude"])

    # 3. Filter within 30km and sort by distance
    nearby = [h for h in all_hospitals if h["distance_km"] <= 30]
    nearby.sort(key=lambda h: h["distance_km"])

    if not nearby:
        return {"hospitals": [], "message": "No hospitals found within 30km"}

    # 4. Get ETA for top 5 (limit API calls)
    hospitals = []
    for h in nearby[:5]:
        eta_data = await get_eta_and_distance(
            origin_lat=lat, origin_lng=lng,
            dest_lat=h["latitude"], dest_lng=h["longitude"],
        )

        # Blood type match check
        blood_match = None
        if blood_type:
            blood_match = blood_type in (h.get("blood_types_available") or [])

        # Composite score
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
            "blood_types": h.get("blood_types_available", []),
            "has_trauma": h["has_trauma_center"],
            "has_cath_lab": h["has_cath_lab"],
            "has_neuro": h["has_neuro_unit"],
            "score": score,
        })

    # Sort by composite score (lower = better)
    hospitals.sort(key=lambda h: h["score"])
    response = {"hospitals": hospitals[:3]}

    # Cache for 5 minutes
    await set_cached(cache_key, json.dumps(response), ttl=300)
    return response


# ── GET /api/hospitals ────────────────────────────────────────
@router.get("/")
async def list_hospitals():
    """List all active hospitals (for admin/map views)."""
    hospitals = get_all_hospitals()
    return [
        {
            "id": h["id"],
            "name": h["name"],
            "lat": h["latitude"],
            "lng": h["longitude"],
            "type": h["type"],
            "trauma_beds": h["trauma_beds_available"],
            "icu_beds": h["icu_beds_available"],
        }
        for h in hospitals
    ]


# ── GET /api/hospitals/{hospital_id}/beds ─────────────────────
@router.get("/{hospital_id}/beds")
async def get_bed_status(hospital_id: str):
    """Get current bed counts for a specific hospital."""
    h = get_hospital_by_id(hospital_id)
    if not h:
        return {"error": "Hospital not found"}
    return {
        "hospital_id": hospital_id,
        "trauma_beds": h["trauma_beds_available"],
        "icu_beds": h["icu_beds_available"],
        "general_beds": h["general_beds_available"],
        "blood_bank": h["blood_bank"],
        "blood_types": h.get("blood_types_available", []),
        "updated_at": h["beds_updated_at"],
    }


# ── PATCH /api/hospitals/{hospital_id}/beds ───────────────────
@router.patch("/{hospital_id}/beds")
async def update_bed_status(
    hospital_id: str,
    trauma_beds: Optional[int] = Query(None),
    icu_beds: Optional[int] = Query(None),
    general_beds: Optional[int] = Query(None),
    blood_types: Optional[List[str]] = Query(None),
):
    """Update bed counts (called by hospital staff dashboard / mock updater)."""
    result = update_hospital_beds(
        hospital_id,
        trauma_beds=trauma_beds,
        icu_beds=icu_beds,
        general_beds=general_beds,
        blood_types=blood_types,
    )
    if not result:
        return {"error": "Hospital not found"}

    # Invalidate related cache
    await set_cached(f"beds:{hospital_id}", None, ttl=1)
    return {"updated": True}


# ── GET /api/hospitals/live/{hospital_id} — SSE ───────────────
@router.get("/live/{hospital_id}")
async def live_bed_updates(hospital_id: str):
    """
    Server-Sent Events endpoint.
    Browser connects once, receives bed count updates every 30 seconds.
    Usage: const es = new EventSource('/api/hospitals/live/{id}')
    """
    async def event_generator():
        while True:
            h = get_hospital_by_id(hospital_id)
            if h:
                data = {
                    "hospital_id": hospital_id,
                    "trauma_beds": h["trauma_beds_available"],
                    "icu_beds": h["icu_beds_available"],
                    "general_beds": h["general_beds_available"],
                    "blood_types": h.get("blood_types_available", []),
                    "timestamp": h["beds_updated_at"],
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
