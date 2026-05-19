from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from database import get_db
import models
from services.geo import haversine
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.sql import func

router = APIRouter(prefix="/api/ambulance", tags=["ambulance"])

class LocationUpdate(BaseModel):
    lat: float
    lng: float

class AmbulanceRequest(BaseModel):
    lat: float
    lng: float
    address: str
    patient_name: str
    patient_phone: str
    severity: int = Field(..., ge=1, le=5)

@router.post("/request")
async def request_ambulance(payload: AmbulanceRequest, db: AsyncSession = Depends(get_db)):
    # 1. Save new dispatch_request with status=pending
    dispatch = models.DispatchRequest(
        incident_lat=payload.lat,
        incident_lng=payload.lng,
        incident_address=payload.address,
        status="pending",
        patient_name=payload.patient_name,
        patient_phone=payload.patient_phone,
        severity=payload.severity
    )
    db.add(dispatch)
    await db.flush()  # Generate dispatch.id

    # Create initial audit log
    audit_init = models.AuditLog(
        request_id=dispatch.id,
        event_type="request_created",
        details=f"Emergency request submitted by {payload.patient_name} for location '{payload.address}' (severity level {payload.severity})."
    )
    db.add(audit_init)

    # 2. Find 5 nearest verified+available ambulances using Haversine formula in Python (no PostGIS)
    # Join ambulances and providers where provider is verified and ambulance is available
    query = (
        select(models.Ambulance)
        .join(models.Provider)
        .where(
            models.Ambulance.is_available == True,
            models.Provider.is_verified == True
        )
        .options(selectinload(models.Ambulance.provider))
    )
    result = await db.execute(query)
    ambulances = result.scalars().all()

    # Calculate distance for each
    ambulance_distances = []
    for amb in ambulances:
        dist = haversine(payload.lat, payload.lng, amb.current_lat, amb.current_lng)
        ambulance_distances.append((amb, dist))

    # Sort by distance
    ambulance_distances.sort(key=lambda x: x[1])

    # Take top 5 nearest
    nearest_5 = ambulance_distances[:5]

    if not nearest_5:
        # Commit the request as pending with no ambulance assigned
        await db.commit()
        return {
            "dispatch_request_id": dispatch.id,
            "status": dispatch.status,
            "message": "No available and verified ambulances found in the region.",
            "assigned_ambulance": None,
            "eta_minutes": None
        }

    # 3. Sort by distance, assign the closest one
    closest_amb, closest_dist = nearest_5[0]

    # 4. Set ambulance is_available=False
    closest_amb.is_available = False

    # 5. Update request status=assigned
    dispatch.assigned_ambulance_id = closest_amb.id
    dispatch.status = "assigned"
    dispatch.assigned_at = func.now()

    # Create assignment audit log
    audit_assign = models.AuditLog(
        request_id=dispatch.id,
        event_type="ambulance_assigned",
        details=f"Ambulance {closest_amb.vehicle_number} (Driver: {closest_amb.driver_name}) from provider '{closest_amb.provider.name}' assigned. Distance: {closest_dist:.2f} km."
    )
    db.add(audit_assign)

    await db.commit()
    await db.refresh(dispatch)
    await db.refresh(closest_amb)

    # 6. Return ambulance details + ETA estimate
    # Simple ETA estimation: 1.5 mins per km + 3 mins base delay
    eta_est = round(closest_dist * 1.5 + 3.0, 1)

    return {
        "dispatch_request_id": dispatch.id,
        "status": dispatch.status,
        "assigned_ambulance": {
            "id": closest_amb.id,
            "vehicle_number": closest_amb.vehicle_number,
            "driver_name": closest_amb.driver_name,
            "driver_phone": closest_amb.driver_phone,
            "provider_name": closest_amb.provider.name,
            "current_lat": closest_amb.current_lat,
            "current_lng": closest_amb.current_lng,
            "distance_km": round(closest_dist, 2)
        },
        "eta_minutes": eta_est
    }

@router.get("/nearby")
async def get_nearby_ambulances(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(10.0),
    db: AsyncSession = Depends(get_db)
):
    # Find verified + available ambulances within radius
    query = (
        select(models.Ambulance)
        .join(models.Provider)
        .where(
            models.Ambulance.is_available == True,
            models.Provider.is_verified == True
        )
        .options(selectinload(models.Ambulance.provider))
    )
    result = await db.execute(query)
    ambulances = result.scalars().all()

    nearby_list = []
    for amb in ambulances:
        dist = haversine(lat, lng, amb.current_lat, amb.current_lng)
        if dist <= radius_km:
            nearby_list.append({
                "id": amb.id,
                "provider_id": amb.provider_id,
                "provider_name": amb.provider.name,
                "vehicle_number": amb.vehicle_number,
                "driver_name": amb.driver_name,
                "driver_phone": amb.driver_phone,
                "current_lat": amb.current_lat,
                "current_lng": amb.current_lng,
                "last_ping": amb.last_ping,
                "distance_km": round(dist, 2)
            })

    nearby_list.sort(key=lambda x: x["distance_km"])
    return nearby_list

@router.patch("/{id}/location")
async def update_location(
    id: int,
    payload: LocationUpdate,
    db: AsyncSession = Depends(get_db)
):
    query = select(models.Ambulance).where(models.Ambulance.id == id)
    result = await db.execute(query)
    ambulance = result.scalar_one_or_none()

    if not ambulance:
        raise HTTPException(status_code=404, detail="Ambulance not found")

    ambulance.current_lat = payload.lat
    ambulance.current_lng = payload.lng
    ambulance.last_ping = func.now()

    await db.commit()
    await db.refresh(ambulance)

    return {
        "id": ambulance.id,
        "vehicle_number": ambulance.vehicle_number,
        "current_lat": ambulance.current_lat,
        "current_lng": ambulance.current_lng,
        "last_ping": ambulance.last_ping
    }
