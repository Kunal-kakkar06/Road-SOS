import asyncio
from pydantic import BaseModel
from typing import Optional, Union
import json
from ai.pipeline.orchestrator import get_orchestrator
from ai.schemas.input_schema import AIInput
import uuid

class TriageRequest(BaseModel):
    age: Optional[Union[int, str]] = None
    gender: Optional[str] = None
    symptoms: Optional[str] = None
    consciousness: Optional[str] = None
    breathing: Optional[str] = None
    image_label: Optional[str] = None
    voice_transcript: Optional[str] = None

req = TriageRequest(age=45, symptoms="chest pain", consciousness="Alert", breathing="Normal")

combined_symptoms = req.symptoms or ""
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

ai_input = AIInput(
    request_id=str(uuid.uuid4()),
    symptoms=combined_symptoms.strip() or "General discomfort",
    age=age_int,
    gender=req.gender,
    has_voice=bool(req.voice_transcript),
    voice_transcript=req.voice_transcript,
    has_image=bool(req.image_label),
    image_label=req.image_label,
)

orch = get_orchestrator()
response = orch.process(ai_input)

shap_values = {}
for sf in response.prediction.shap_factors:
    shap_values[sf.feature] = round(sf.impact, 2)
    
if not shap_values:
    shap_values = {"symptoms": 20.0}

symptoms_list = [s.strip() for s in (req.symptoms or "").split(",") if s.strip()]
if not symptoms_list:
    symptoms_list = ["General discomfort"]
if req.image_label:
    symptoms_list.append(f"Image finding: {req.image_label}")
if req.voice_transcript:
    symptoms_list.append("Voice reported symptoms")

assessment = response.explanation or response.decision.reasoning or "Triage completed successfully."

out = {
    "severity_score": int(response.prediction.confidence * 100),
    "severity_level": response.prediction.severity_class.name.title(),
    "symptoms_extracted": symptoms_list,
    "assessment": assessment,
    "actions": response.decision.actions,
    "eta_minutes": response.decision.estimated_eta_minutes,
    "shap_values": shap_values,
}

print(json.dumps(out, indent=2))
