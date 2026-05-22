from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import os
import logging
import json

router = APIRouter()
logger = logging.getLogger("roadsos.triage")

# Request/Response models
class TriageRequest(BaseModel):
    age: Optional[Union[int, str]] = None
    gender: Optional[str] = None
    symptoms: Optional[str] = None
    consciousness: Optional[str] = None
    breathing: Optional[str] = None
    image_label: Optional[str] = None
    voice_transcript: Optional[str] = None

class TriageResponse(BaseModel):
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

@router.post("/api/triage", response_model=TriageResponse)
async def triage(req: TriageRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    is_mock = not api_key or "your" in api_key.lower() or "placeholder" in api_key.lower()
    if is_mock:
        logger.info("Using mock triage engine (no valid Anthropic key set)")
        return get_mock_triage(
            req.age, req.gender, req.symptoms or "", req.consciousness or "Alert", req.breathing or "Normal", req.image_label, req.voice_transcript
        )
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        prompt = f"""You are an emergency medical AI triage assistant.
Analyze the following patient information:
- Age: {req.age}\n- Gender: {req.gender}\n- Symptoms: {req.symptoms}\n- Consciousness: {req.consciousness}\n- Breathing: {req.breathing}\n- Image label: {req.image_label}\n- Voice transcript: {req.voice_transcript}\n\nReturn a JSON object matching the TriageResponse schema. Do not include any explanations outside the JSON.\n"""
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text.strip()
        # Strip optional markdown fences
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        data = json.loads(response_text)
        return data
    except Exception as e:
        logger.error(f"Anthropic API error: {e}, falling back to mock")
        return get_mock_triage(
            req.age, req.gender, req.symptoms or "", req.consciousness or "Alert", req.breathing or "Normal", req.image_label, req.voice_transcript
        )

@router.post("/api/triage/image", response_model=TriageImageResponse)
async def triage_image(file: Optional[UploadFile] = File(None)):
    # Stub implementation – in a real system this would invoke an image classification model.
    return {"label": "Visible deep cut/bleeding", "confidence": 0.92}

@router.post("/api/triage/voice", response_model=TriageVoiceResponse)
async def triage_voice(file: Optional[UploadFile] = File(None)):
    # Stub implementation – would normally run a speech‑to‑text model.
    return {"transcript": "I am feeling dizzy, have strong chest pain and cannot breathe properly."}
