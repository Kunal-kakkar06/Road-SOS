from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from database import get_db
import models
from pydantic import BaseModel
from sqlalchemy.sql import func

router = APIRouter(prefix="/api/dispatch", tags=["dispatch"])

class StatusUpdate(BaseModel):
    status: str  # pending/assigned/en_route/arrived/completed/cancelled

@router.get("/{id}")
async def get_dispatch(id: int, db: AsyncSession = Depends(get_db)):
    query = (
        select(models.DispatchRequest)
        .where(models.DispatchRequest.id == id)
        .options(
            selectinload(models.DispatchRequest.assigned_ambulance)
            .selectinload(models.Ambulance.provider),
            selectinload(models.DispatchRequest.audit_logs)
        )
    )
    result = await db.execute(query)
    dispatch = result.scalar_one_or_none()

    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch request not found")

    # Format return payload
    assigned_amb_data = None
    if dispatch.assigned_ambulance:
        assigned_amb_data = {
            "id": dispatch.assigned_ambulance.id,
            "vehicle_number": dispatch.assigned_ambulance.vehicle_number,
            "driver_name": dispatch.assigned_ambulance.driver_name,
            "driver_phone": dispatch.assigned_ambulance.driver_phone,
            "provider_name": dispatch.assigned_ambulance.provider.name,
            "current_lat": dispatch.assigned_ambulance.current_lat,
            "current_lng": dispatch.assigned_ambulance.current_lng
        }

    audit_logs_data = []
    for log in dispatch.audit_logs:
        audit_logs_data.append({
            "id": log.id,
            "event_type": log.event_type,
            "details": log.details,
            "created_at": log.created_at
        })
    audit_logs_data.sort(key=lambda x: x["created_at"])

    return {
        "id": dispatch.id,
        "incident_lat": dispatch.incident_lat,
        "incident_lng": dispatch.incident_lng,
        "incident_address": dispatch.incident_address,
        "status": dispatch.status,
        "patient_name": dispatch.patient_name,
        "patient_phone": dispatch.patient_phone,
        "severity": dispatch.severity,
        "requested_at": dispatch.requested_at,
        "assigned_at": dispatch.assigned_at,
        "arrived_at": dispatch.arrived_at,
        "completed_at": dispatch.completed_at,
        "assigned_ambulance": assigned_amb_data,
        "audit_logs": audit_logs_data
    }

@router.patch("/{id}/status")
async def update_status(
    id: int,
    payload: StatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    valid_statuses = ["pending", "assigned", "en_route", "arrived", "completed", "cancelled"]
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    query = (
        select(models.DispatchRequest)
        .where(models.DispatchRequest.id == id)
        .options(selectinload(models.DispatchRequest.assigned_ambulance))
    )
    result = await db.execute(query)
    dispatch = result.scalar_one_or_none()

    if not dispatch:
        raise HTTPException(status_code=404, detail="Dispatch request not found")

    old_status = dispatch.status
    new_status = payload.status

    if old_status == new_status:
        return {"message": "Status already set to this value", "id": dispatch.id, "status": dispatch.status}

    dispatch.status = new_status

    # Handle state transitions and timestamps
    if new_status == "arrived":
        dispatch.arrived_at = func.now()
    elif new_status == "completed":
        dispatch.completed_at = func.now()
        # If status=completed → set ambulance is_available=True
        if dispatch.assigned_ambulance:
            dispatch.assigned_ambulance.is_available = True
    elif new_status == "cancelled":
        # If cancelled, free up the ambulance too
        if dispatch.assigned_ambulance:
            dispatch.assigned_ambulance.is_available = True

    # Save transition to audit logs
    audit_log = models.AuditLog(
        request_id=dispatch.id,
        event_type="status_changed",
        details=f"Dispatch status updated from '{old_status}' to '{new_status}'."
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(dispatch)

    return {
        "id": dispatch.id,
        "status": dispatch.status,
        "arrived_at": dispatch.arrived_at,
        "completed_at": dispatch.completed_at,
        "ambulance_available": dispatch.assigned_ambulance.is_available if dispatch.assigned_ambulance else None
    }
