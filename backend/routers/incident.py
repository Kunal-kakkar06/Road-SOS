from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
import uuid
import os

from database import get_db
from models import Incident, IncidentEvent, FIRTemplate
from schemas import CreateIncidentRequest, AddEventRequest
from services.pdf_service import generate_incident_pdf
from services.cloudinary_service import upload_photo

router = APIRouter(prefix="/api/incident", tags=["Incident"])


class UpdateIncidentRequest(BaseModel):
    address:         Optional[str] = None
    speed_at_impact: Optional[float] = None
    ambulance_name:  Optional[str] = None
    hospital_name:   Optional[str] = None
    severity:        Optional[str] = None


# ── PATCH /api/incident/{incident_id} ─────────────────────────────
@router.patch("/{incident_id}")
async def update_incident(
    incident_id: str,
    payload:     UpdateIncidentRequest,
    db:          AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Incident).filter(Incident.incident_id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if payload.address is not None:         incident.address = payload.address
    if payload.speed_at_impact is not None: incident.speed_at_impact = payload.speed_at_impact
    if payload.ambulance_name is not None:  incident.ambulance_name = payload.ambulance_name
    if payload.hospital_name is not None:   incident.hospital_name = payload.hospital_name
    if payload.severity is not None:        incident.severity = payload.severity

    db.add(IncidentEvent(
        incident_id = incident_id,
        event_type  = "incident_updated",
        description = "Incident audit details updated manually",
    ))
    
    await db.commit()
    return {"updated": True}



# ── POST /api/incident/create ─────────────────────────────────
@router.post("/create")
async def create_incident(payload: CreateIncidentRequest, db: AsyncSession = Depends(get_db)):
    incident_id = str(uuid.uuid4())
    
    # We convert severity format if needed or save directly
    incident = Incident(
        incident_id     = incident_id,
        user_id         = payload.user_id,
        sos_event_id    = payload.sos_event_id,
        crash_event_id  = payload.crash_event_id,
        dispatch_id     = payload.dispatch_id,
        latitude        = payload.latitude,
        longitude       = payload.longitude,
        severity        = payload.severity,
        speed_at_impact = payload.speed_at_impact,
        medical_profile = payload.medical_profile,
        hospital_name   = payload.hospital_name,
        ambulance_name  = payload.ambulance_name,
        crash_timestamp = datetime.utcnow(),
        fir_state       = payload.fir_state or "Karnataka",
    )
    db.add(incident)
    
    event = IncidentEvent(
        incident_id = incident_id,
        event_type  = "incident_created",
        description = "Incident record opened",
    )
    db.add(event)
    
    await db.commit()
    return {"incident_id": incident_id, "status": "created"}


# ── POST /api/incident/{id}/event ─────────────────────────────
@router.post("/{incident_id}/event")
async def add_event(incident_id: str, payload: AddEventRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).filter(Incident.incident_id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    ts = datetime.fromisoformat(payload.timestamp.replace("Z", "")) if payload.timestamp else datetime.utcnow()
    
    db.add(IncidentEvent(
        incident_id = incident_id,
        event_type  = payload.event_type,
        description = payload.description,
        event_metadata = payload.metadata,
        timestamp   = ts,
    ))

    # Live update fields based on timeline events
    if payload.event_type == "ambulance_dispatched" and payload.metadata:
        incident.ambulance_name = payload.metadata.get("ambulance_name") or payload.metadata.get("driver_name")
    elif payload.event_type == "hospital_admitted":
        incident.hospital_name = payload.description or payload.metadata.get("hospital_name")

    await db.commit()
    return {"logged": True}


# ── POST /api/incident/{id}/photos ────────────────────────────
@router.post("/{incident_id}/photos")
async def upload_photos(
    incident_id: str,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Incident).filter(Incident.incident_id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    uploaded = []
    for file in files:
        contents = await file.read()
        url = await upload_photo(
            file_bytes = contents,
            filename   = f"{incident_id}_{file.filename}",
            folder     = f"roadsos/incidents/{incident_id}",
        )
        if url:
            uploaded.append({
                "url": url,
                "filename": file.filename,
                "uploaded_at": datetime.utcnow().isoformat()
            })

    # Save to JSON column
    incident.photo_urls = (incident.photo_urls or []) + uploaded
    
    # Log timeline event for photo uploading
    db.add(IncidentEvent(
        incident_id = incident_id,
        event_type  = "evidence_uploaded",
        description = f"Uploaded {len(uploaded)} photo evidence item(s).",
    ))
    
    await db.commit()
    return {"uploaded": len(uploaded), "photos": uploaded}


# ── POST /api/incident/{id}/generate-pdf ─────────────────────
@router.post("/{incident_id}/generate-pdf")
async def generate_pdf(incident_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).filter(Incident.incident_id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    result_events = await db.execute(
        select(IncidentEvent)
        .filter(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.timestamp.asc())
    )
    events = result_events.scalars().all()

    # Generate PDF in thread to keep ASGI server responsive
    import asyncio
    loop = asyncio.get_event_loop()
    pdf_path = await loop.run_in_executor(None, generate_incident_pdf, incident, events)
    
    incident.pdf_url = pdf_path
    
    db.add(IncidentEvent(
        incident_id = incident_id,
        event_type  = "report_generated",
        description = "Official PDF report compiled and generated",
    ))
    
    await db.commit()

    return {
        "pdf_path": pdf_path,
        "download_url": f"/api/incident/{incident_id}/download-pdf"
    }


# ── GET /api/incident/{id}/download-pdf ──────────────────────
@router.get("/{incident_id}/download-pdf")
async def download_pdf(incident_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).filter(Incident.incident_id == incident_id))
    incident = result.scalars().first()
    if not incident or not incident.pdf_url:
        raise HTTPException(status_code=404, detail="PDF not generated yet")
    if not os.path.exists(incident.pdf_url):
        raise HTTPException(status_code=404, detail="PDF file missing on server")
    
    short_id = incident_id[:8].upper()
    return FileResponse(
        path       = incident.pdf_url,
        filename   = f"RoadSOS_Incident_{short_id}.pdf",
        media_type = "application/pdf",
    )


# ── GET /api/incident/{id} ────────────────────────────────────
@router.get("/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).filter(Incident.incident_id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    result_events = await db.execute(
        select(IncidentEvent)
        .filter(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.timestamp.asc())
    )
    events = result_events.scalars().all()

    return {
        "incident_id":    incident.incident_id,
        "severity":       incident.severity,
        "crash_timestamp":str(incident.crash_timestamp),
        "latitude":       incident.latitude,
        "longitude":      incident.longitude,
        "address":        incident.address,
        "speed_at_impact":incident.speed_at_impact,
        "hospital_name":  incident.hospital_name,
        "ambulance_name": incident.ambulance_name,
        "medical_profile":incident.medical_profile,
        "photo_urls":     incident.photo_urls or [],
        "pdf_url":        incident.pdf_url,
        "status":         incident.status,
        "fir_state":      incident.fir_state,
        "timeline": [
            {
                "event_type": e.event_type, 
                "description": e.description,
                "metadata": e.event_metadata, 
                "timestamp": str(e.timestamp)
            }
            for e in events
        ],
    }


# ── GET /api/incident/user/{user_id} ─────────────────────────
@router.get("/user/{user_id}")
async def get_user_incidents(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Incident)
        .filter(Incident.user_id == user_id)
        .order_by(Incident.created_at.desc())
    )
    incidents = result.scalars().all()
    return [
        {
            "incident_id": i.incident_id, 
            "severity": i.severity,
            "crash_timestamp": str(i.crash_timestamp), 
            "address": i.address,
            "hospital_name": i.hospital_name, 
            "status": i.status,
            "has_pdf": bool(i.pdf_url), 
            "photo_count": len(i.photo_urls or [])
        }
        for i in incidents
    ]


# ── GET /api/incident/{id}/fir-guide ─────────────────────────
@router.get("/{incident_id}/fir-guide")
async def get_fir_guide(incident_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Incident).filter(Incident.incident_id == incident_id))
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    state    = incident.fir_state or "Karnataka"
    result_tpl = await db.execute(select(FIRTemplate).filter(FIRTemplate.state == state))
    template = result_tpl.scalars().first()
    if not template:
        # Fallback to whatever is available
        result_fallback = await db.execute(select(FIRTemplate))
        template = result_fallback.scalars().first()
        if not template:
            raise HTTPException(status_code=404, detail=f"No FIR template for {state}")
            
    return {"state": template.state, "incident_id": incident_id, "steps": template.steps}
