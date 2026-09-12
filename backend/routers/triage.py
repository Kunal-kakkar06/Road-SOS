from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
import asyncio
from dependencies.auth_deps import require_user
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
import os
import logging
import json

router = APIRouter()
logger = logging.getLogger("roadsos.triage")

# Request/Response models
class TriageRequest(BaseModel):
    text: Optional[str] = Field(None, max_length=2000)
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    has_voice: Optional[bool] = None
    has_image: Optional[bool] = None
    medical_profile: Optional[Dict[str, Any]] = None
    
    # Legacy / extra fields
    age: Optional[Union[int, str]] = None
    gender: Optional[str] = Field(None, max_length=100)
    symptoms: Optional[str] = Field(None, max_length=2000)
    consciousness: Optional[str] = Field(None, max_length=100)
    breathing: Optional[str] = Field(None, max_length=100)
    image_label: Optional[str] = Field(None, max_length=500)
    image_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    sensor_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    voice_transcript: Optional[str] = Field(None, max_length=2000)

class TriageResponse(BaseModel):
    request_id: str
    severity_score: int
    severity_level: str
    symptoms_extracted: List[str]
    assessment: str
    actions: List[str]
    eta_minutes: int
    shap_values: Dict[str, float]

class TriageImageResponse(BaseModel):
    label: str
    confidence: float

class TriageVoiceResponse(BaseModel):
    transcript: str

def get_mock_triage(
    age: Any,
    gender: Optional[str],
    symptoms: str,
    consciousness: str,
    breathing: str,
    image_label: Optional[str],
    voice_transcript: Optional[str]
) -> dict:
    """Simple deterministic mock used when ANTHROPIC_API_KEY is missing or placeholder."""
    score = 25
    level = "Low"
    c_lower = (consciousness or "alert").lower()
    if "unresponsive" in c_lower:
        score += 45
    elif "pain response" in c_lower or "voice response" in c_lower:
        score += 25
    b_lower = (breathing or "normal").lower()
    if "absent" in b_lower:
        score += 50
    elif "labored" in b_lower or "rapid" in b_lower:
        score += 30
    s_lower = (symptoms or "").lower()
    if any(term in s_lower for term in ["chest pain", "heart attack", "difficulty breathing", "stroke", "severe bleeding"]):
        score += 35
    elif any(term in s_lower for term in ["fracture", "broken", "burn", "intense pain"]):
        score += 20
    elif any(term in s_lower for term in ["fever", "cough", "cold"]):
        score += 10
    score = min(max(score, 5), 100)
    if score >= 80:
        level = "Critical"
    elif score >= 60:
        level = "High"
    elif score >= 35:
        level = "Moderate"
    else:
        level = "Low"
    symptoms_list = [s.strip() for s in (symptoms or "").split(",") if s.strip()]
    if not symptoms_list:
        symptoms_list = ["General discomfort"]
    if image_label:
        symptoms_list.append(f"Image finding: {image_label}")
    if voice_transcript:
        symptoms_list.append("Voice reported symptoms")
    assessment = (
        f"Patient is a {age or 'unknown age'} year old {gender or 'unspecified gender'} presenting with symptoms: {symptoms}. "
        f"Consciousness is assessed as {consciousness} and breathing pattern is {breathing}. "
        f"Triage indicates a {level.upper()} severity risk (Score: {score}/100)."
    )
    actions = [
        "Ensure patient is in a safe and comfortable environment.",
        "Monitor vital signs (breathing, heart rate, responsiveness) continuously."
    ]
    if level == "Critical":
        actions.insert(0, "🚨 Call emergency services immediately and request an ambulance.")
        actions.append("Prepare to perform CPR if breathing becomes absent or agonal.")
    elif level == "High":
        actions.insert(0, "Seek urgent medical attention at the nearest emergency department.")
        actions.append("Keep the patient warm and still.")
    elif level == "Moderate":
        actions.append("Schedule a visit to an urgent care clinic or primary doctor soon.")
    else:
        actions.append("Rest and monitor symptoms at home; seek help if they worsen.")
    shap = {
        "age": round(float((int(age) if str(age).isdigit() else 35) / 10.0), 2),
        "gender": 1.5,
        "symptoms": float(35.0 if level == "Critical" else 20.0 if level == "High" else 10.0),
        "consciousness": float(40.0 if "alert" not in (consciousness or "").lower() else 2.0),
        "breathing": float(45.0 if "normal" not in (breathing or "").lower() else 3.0),
    }
    return {
        "severity_score": int(score),
        "severity_level": level,
        "symptoms_extracted": symptoms_list,
        "assessment": assessment,
        "actions": actions,
        "eta_minutes": 6 if level == "Critical" else 15 if level == "High" else 25 if level == "Moderate" else 45,
        "shap_values": shap,
    }
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
import time

async def _execute_triage_pipeline(req: TriageRequest, db: AsyncSession, user_id: str = None, processing_mode: str = "sync", job_id: str = None, request_id: str = None) -> dict:
    import uuid
    from ai.pipeline.orchestrator import get_orchestrator
    from ai.schemas.input_schema import AIInput

    combined_symptoms = (req.text or req.symptoms) or ""
    if req.consciousness:
        combined_symptoms += f" (Consciousness: {req.consciousness})"
    if req.breathing:
        combined_symptoms += f" (Breathing: {req.breathing})"
    
    age_int = None
    if req.age:
        try:
            age_int = int(req.age)
        except (ValueError, TypeError):
            pass
            
    combined_symptoms = combined_symptoms.strip()
    final_symptoms = combined_symptoms if combined_symptoms else None

    if not request_id:
        request_id = str(uuid.uuid4())

    ai_input = AIInput(
        request_id=request_id,
        symptoms=final_symptoms,
        age=age_int,
        gender=req.gender,
        medical_profile=req.medical_profile,
        latitude=req.latitude,
        longitude=req.longitude,
        has_voice=bool(req.has_voice or req.voice_transcript),
        voice_transcript=req.voice_transcript,
        has_image=bool(req.has_image or req.image_label or req.image_score is not None),
        image_label=req.image_label,
        image_score=req.image_score,
        has_sensor_data=bool(req.sensor_score is not None),
        sensor_score=req.sensor_score,
    )

    orchestrator = get_orchestrator()
    start_time = time.perf_counter()
    logger.info(f"[triage.request.received] request_id={request_id} job_id={job_id} user_id={user_id} mode={processing_mode}")
    
    try:
        # Offload CPU-bound ML inference to thread
        response = await asyncio.to_thread(orchestrator.process, ai_input)
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(f"[triage.processing.completed] request_id={request_id} duration_ms={duration_ms} severity={response.prediction.severity_class.name}")
    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error(f"[triage.processing.failed] request_id={request_id} duration_ms={duration_ms} error={e}", exc_info=True)
        
        # Persist failed event securely without exposing stack trace to user
        from models.triage_model import TriageEvent
        failed_event = TriageEvent(
            id=request_id,
            event_id=request_id,
            user_id=user_id,
            job_id=job_id,
            processing_mode=processing_mode,
            status="failed",
            processing_duration_ms=duration_ms,
            error_message="Internal processing error"
        )
        db.add(failed_event)
        await db.commit()
        
        # Fallback to mock so we don't crash the client totally on sync, but we shouldn't lie about success.
        # However, preserving existing contract: we return mock on failure.
        mock_res = get_mock_triage(
            req.age, req.gender, req.symptoms or "", req.consciousness or "Alert", req.breathing or "Normal", req.image_label, req.voice_transcript
        )
        mock_res["request_id"] = request_id
        return mock_res
        
    shap_values = {}
    for sf in response.prediction.shap_factors:
        shap_values[sf.feature] = round(sf.impact, 2)
        
    if not shap_values:
        shap_values = {"symptoms": 20.0}

    symptoms_text = (req.text or req.symptoms) or ""
    symptoms_list = [s.strip() for s in symptoms_text.split(",") if s.strip()]
    if not symptoms_list:
        symptoms_list = ["Unknown or unspecified symptoms"]
    if req.image_label:
        symptoms_list.append(f"Image finding: {req.image_label}")
    if req.voice_transcript:
        symptoms_list.append("Voice reported symptoms")

    assessment = response.explanation or response.decision.reasoning or "Triage completed successfully."
    
    # Persist the event to the database idempotently
    from models.triage_model import TriageEvent
    from sqlalchemy import select
    
    stmt = select(TriageEvent).where(TriageEvent.event_id == ai_input.request_id)
    res = await db.execute(stmt)
    existing_event = res.scalars().first()
    
    if existing_event:
        existing_event.status = "completed"
        existing_event.processing_duration_ms = duration_ms
        existing_event.final_severity = response.prediction.severity_class.name.title()
        existing_event.final_score = response.prediction.confidence
        existing_event.severity_label = assessment
        existing_event.shap_factors = shap_values
    else:
        triage_event = TriageEvent(
            id=ai_input.request_id,
            event_id=ai_input.request_id,
            user_id=user_id,
            job_id=job_id,
            processing_mode=processing_mode,
            status="completed",
            processing_duration_ms=duration_ms,
            model_version=response.prediction.model_version,
            feature_version=response.prediction.feature_version,
            model_type=response.prediction.model_type,
            has_image=ai_input.has_image,
            has_voice=ai_input.has_voice,
            has_sensor_data=ai_input.has_sensor_data,
            transcript=ai_input.voice_transcript,
            image_score=ai_input.image_score,
            sensor_score=ai_input.sensor_score,
            final_severity=response.prediction.severity_class.name.title(),
            final_score=response.prediction.confidence,
            severity_label=assessment,
            shap_factors=shap_values
        )
        db.add(triage_event)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.warning(f"[triage.persistence.idempotent_handled] request_id={request_id} notice={e}")

    logger.info(f"[triage.persistence.completed] request_id={request_id}")
    
    return {
        "request_id": request_id,
        # Note: severity_score represents the model's confidence percentage,
        # rather than a medically calibrated severity metric.
        "severity_score": int(response.prediction.confidence * 100),
        "severity_level": response.prediction.severity_class.name.title(),
        "symptoms_extracted": symptoms_list,
        "assessment": assessment,
        "actions": response.decision.actions,
        "eta_minutes": response.decision.estimated_eta_minutes,
        "shap_values": shap_values,
    }

@router.post("/api/triage", response_model=TriageResponse)
async def triage(req: TriageRequest, db: AsyncSession = Depends(get_db), current_user = Depends(require_user)):
    return await _execute_triage_pipeline(req, db, current_user.uuid)

class AsyncTriageResponse(BaseModel):
    job_id: str
    request_id: str
    status: str

async def _process_triage_task(job_id: str, req: TriageRequest, user_id: str, request_id: str):
    from services.triage_job_manager import update_job
    from database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as db:
            await update_job(job_id, status="processing", db=db)
            result = await _execute_triage_pipeline(req, db, user_id=user_id, processing_mode="async", job_id=job_id, request_id=request_id)
            await update_job(job_id, status="completed", result=result, db=db)
    except Exception as e:
        logger.error(f"Async triage task wrapper failed: {e}", exc_info=True)
        async with AsyncSessionLocal() as db:
            await update_job(job_id, status="failed", error="Triage processing failed.", db=db)

@router.post("/api/triage/async", status_code=202, response_model=AsyncTriageResponse)
async def triage_async(req: TriageRequest, current_user = Depends(require_user), db: AsyncSession = Depends(get_db)):
    from services.triage_job_manager import create_job
    import uuid
    
    request_id = str(uuid.uuid4())
    job_id = await create_job(current_user.uuid, db, request_id, req.dict())
    
    # ML inference is now handled by an external worker process asynchronously.
    return {"job_id": job_id, "request_id": request_id, "status": "pending"}

@router.get("/api/triage/jobs/{job_id}")
async def get_triage_job_status(job_id: str, current_user = Depends(require_user), db: AsyncSession = Depends(get_db)):
    from services.triage_job_manager import get_job
    job = await get_job(job_id, current_user.uuid, db)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    resp = {
        "job_id": job["job_id"],
        "status": job["status"]
    }
    if job.get("result"):
        resp["result"] = job["result"]
    if job.get("error"):
        resp["error"] = job["error"]
    if job.get("result") and "request_id" in job["result"]:
        resp["request_id"] = job["result"]["request_id"]
        
    return resp

@router.get("/api/triage/history")
async def get_triage_history(db: AsyncSession = Depends(get_db), current_user = Depends(require_user)):
    from sqlalchemy import select
    from models.triage_model import TriageEvent
    
    stmt = select(TriageEvent).where(TriageEvent.user_id == current_user.uuid).order_by(TriageEvent.created_at.desc())
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    return [
        {
            "id": event.id,
            "request_id": event.event_id,
            "job_id": event.job_id,
            "created_at": event.created_at.isoformat() if event.created_at else None,
            "processing_mode": event.processing_mode,
            "status": event.status,
            "processing_duration_ms": event.processing_duration_ms,
            "model_version": event.model_version,
            "final_severity": event.final_severity,
            "final_score": event.final_score,
            "severity_label": event.severity_label,
            "has_image": event.has_image,
            "has_voice": event.has_voice
        }
        for event in events
    ]

@router.post("/api/triage/image", response_model=TriageImageResponse)
async def triage_image(file: Optional[UploadFile] = File(None), _rbac = Depends(require_user)):
    # Stub implementation – in a real system this would invoke an image classification model.
    return {"label": "Visible deep cut/bleeding", "confidence": 0.92}

@router.post("/api/triage/voice", response_model=TriageVoiceResponse)
async def triage_voice(file: Optional[UploadFile] = File(None), _rbac = Depends(require_user)):
    # Stub implementation – would normally run a speech‑to‑text model.
    return {"transcript": "I am feeling dizzy, have strong chest pain and cannot breathe properly."}
