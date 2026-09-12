import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List

from database import get_db
from models.user import User, ResponderAssignment
from models.incident_model import Incident, IncidentEvent
from dependencies.auth_deps import require_responder
from schemas import ResponderEmergencyStatusUpdate

router = APIRouter(
    prefix="/api/responder",
    tags=["Responder Management"],
    dependencies=[Depends(require_responder)]
)

def serialize_incident(inc: Incident) -> dict:
    return {
        "id": str(inc.id),
        "incident_id": inc.incident_id,
        "user_id": inc.user_id,
        "sos_event_id": inc.sos_event_id,
        "crash_event_id": inc.crash_event_id,
        "dispatch_id": inc.dispatch_id,
        "latitude": inc.latitude,
        "longitude": inc.longitude,
        "address": inc.address,
        "severity": inc.severity,
        "crash_timestamp": inc.crash_timestamp.isoformat() if inc.crash_timestamp else None,
        "speed_at_impact": inc.speed_at_impact,
        "medical_profile": inc.medical_profile,
        "hospital_name": inc.hospital_name,
        "ambulance_name": inc.ambulance_name,
        "status": inc.status,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "updated_at": inc.updated_at.isoformat() if inc.updated_at else None
    }

@router.get("/queue")
async def get_emergency_queue(db: AsyncSession = Depends(get_db)):
    stmt = select(Incident).filter(
        Incident.status != "resolved",
        Incident.status != "completed",
        Incident.status != "closed"
    ).order_by(Incident.created_at.desc())
    
    result = await db.execute(stmt)
    incidents = result.scalars().all()
    return [serialize_incident(i) for i in incidents]

@router.get("/assigned")
async def get_assigned_emergencies(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_responder)):
    stmt = (
        select(Incident)
        .join(ResponderAssignment, ResponderAssignment.incident_id == Incident.incident_id)
        .filter(ResponderAssignment.responder_uuid == current_user.uuid)
        .order_by(Incident.created_at.desc())
    )
    result = await db.execute(stmt)
    incidents = result.scalars().all()
    return [serialize_incident(i) for i in incidents]

@router.patch("/emergency/{incident_id}")
async def update_emergency_status(
    incident_id: str,
    payload: ResponderEmergencyStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_responder)
):
    stmt = select(Incident).filter(Incident.incident_id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    # Update status and log comments
    incident.status = payload.status
    if payload.notes:
        incident.ambulance_name = f"Responder: {current_user.name} ({payload.notes})"
    else:
        incident.ambulance_name = f"Responder: {current_user.name}"
        
    # Ensure responder assignment exists
    assign_stmt = select(ResponderAssignment).filter(
        ResponderAssignment.incident_id == incident_id,
        ResponderAssignment.responder_uuid == current_user.uuid
    )
    assign_result = await db.execute(assign_stmt)
    assignment = assign_result.scalars().first()
    
    if not assignment:
        assignment = ResponderAssignment(
            responder_uuid=current_user.uuid,
            incident_id=incident_id,
            notes=payload.notes
        )
        db.add(assignment)
    else:
        if payload.notes:
            assignment.notes = payload.notes
            
    # Add an audit event log
    event = IncidentEvent(
        incident_id=incident_id,
        event_type="responder_status_updated",
        description=f"Status updated to '{payload.status}' by Responder {current_user.name}."
    )
    db.add(event)
    
    await db.commit()
    await db.refresh(incident)
    return serialize_incident(incident)
