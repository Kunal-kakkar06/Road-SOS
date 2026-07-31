import uvicorn
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import engine, Base
from dotenv import load_dotenv

from routers import ambulance, dispatch, medical_profile, digilocker, voice_guidance, anti_gravity, hospitals, incident, family, triage, sos, crash, prevention
from fastapi.staticfiles import StaticFiles

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created/ensured on startup.")

    # Ensure demo incident exists in database for clean editing audits
    from database import AsyncSessionLocal
    from models import Incident
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Incident).filter(Incident.incident_id == "demo-incident-uuid"))
        exists = result.scalars().first()
        if not exists:
            demo_record = Incident(
                incident_id="demo-incident-uuid",
                user_id="anonymous",
                fir_state="Karnataka",
                severity="P2",
                address=None,
                latitude=12.9716,
                longitude=77.5946,
                speed_at_impact=None,
                ambulance_name=None,
                hospital_name=None
            )
            session.add(demo_record)
            await session.commit()
            print("Seeded blank demo-incident-uuid successfully.")

        # 1. Auto-seed hospitals if empty
        from models.hospital_model import Hospital
        from data.seed_hospitals import BENGALURU_HOSPITALS
        h_result = await session.execute(select(Hospital))
        if not h_result.scalars().first():
            print("Auto-seeding hospitals...")
            for h in BENGALURU_HOSPITALS:
                hospital = Hospital(
                    name=h["name"],
                    address=h["address"],
                    phone=h.get("phone"),
                    type=h["type"],
                    location=None,
                    latitude=h["lat"],
                    longitude=h["lng"],
                    trauma_beds_total=h["trauma_beds_total"],
                    trauma_beds_available=h["trauma_beds_available"],
                    icu_beds_total=h["icu_beds_total"],
                    icu_beds_available=h["icu_beds_available"],
                    general_beds_available=h["general_beds_available"],
                    blood_bank=h["blood_bank"],
                    blood_types_available=h["blood_types_available"],
                    has_trauma_center=h["has_trauma_center"],
                    has_cath_lab=h["has_cath_lab"],
                    has_neuro_unit=h["has_neuro_unit"],
                )
                session.add(hospital)
            await session.commit()
            print("Auto-seeded hospitals successfully.")

        # 2. Auto-seed providers and ambulances if empty
        from models import Provider, Ambulance
        from seed import providers_data, locations
        import datetime
        p_result = await session.execute(select(Provider))
        if not p_result.scalars().first():
            print("Auto-seeding providers and ambulances...")
            db_providers = []
            for p in providers_data:
                prov = Provider(
                    name=p["name"],
                    licence_number=p["licence_number"],
                    licence_expiry=datetime.date(2030, 1, 1),
                    is_verified=True,
                    contact_phone=p["contact_phone"]
                )
                session.add(prov)
                db_providers.append(prov)
            await session.flush()

            ambulance_index = 1
            for i, prov in enumerate(db_providers):
                for j in range(2):
                    loc_idx = (i * 2 + j) % len(locations)
                    loc = locations[loc_idx]
                    noise_lat = ((i * 3 + j * 7) % 10 - 5) * 0.002
                    noise_lng = ((i * 7 + j * 3) % 10 - 5) * 0.002

                    amb = Ambulance(
                        provider_id=prov.id,
                        vehicle_number=f"KA-03-EM-{1000 + ambulance_index}",
                        driver_name=f"Driver {ambulance_index}",
                        driver_phone=f"+9199000{10000 + ambulance_index}",
                        is_available=True,
                        current_lat=loc["lat"] + noise_lat,
                        current_lng=loc["lng"] + noise_lng,
                        last_ping=datetime.datetime.now()
                    )
                    session.add(amb)
                    ambulance_index += 1
            await session.commit()
            print("Auto-seeded providers and ambulances successfully.")
    yield


app = FastAPI(
    title="RoadSOS Emergency Backend API",
    description="Backend API for emergency road assistance, real-time tracking, dispatch routing and triage management.",
    version="1.0.0",
    lifespan=lifespan
)

allow_origins = [
    os.getenv("FRONTEND_ORIGIN", "http://localhost:5173"),
    "https://sos-nine-orcin.vercel.app",          # Vercel production
    "https://*.vercel.app",                         # All Vercel preview deployments
    "http://localhost:5173",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:8080",
    "http://localhost:8082",
    "null",  # file:// origin
    "*"
]

# CORS middleware allowing all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (audio, etc.)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register routers
app.include_router(ambulance.router)
app.include_router(dispatch.router)
app.include_router(medical_profile.router)
app.include_router(digilocker.router)
app.include_router(voice_guidance.router)
app.include_router(anti_gravity.router)
app.include_router(hospitals.router)
app.include_router(incident.router)
app.include_router(family.router)
app.include_router(triage.router)
app.include_router(sos.router)
app.include_router(crash.router)
app.include_router(prevention.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to RoadSOS Emergency API Backend Service",
        "status": "online",
        "endpoints": {
            "api_doc": "/docs",
            "request_ambulance": "POST /api/ambulance/request",
            "nearby_ambulances": "GET /api/ambulance/nearby",
            "update_location": "PATCH /api/ambulance/{id}/location",
            "get_dispatch": "GET /api/dispatch/{id}",
            "update_dispatch_status": "PATCH /api/dispatch/{id}/status"
        }
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "RoadSOS API"}

import logging
import json
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel
from fastapi import UploadFile, File

logger = logging.getLogger("roadsos.triage")

# Triage Request and Response Models
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
    score = 25
    level = "Low"
    
    c_lower = consciousness.lower() if consciousness else "alert"
    if "unresponsive" in c_lower:
        score += 45
    elif "pain response" in c_lower or "voice response" in c_lower:
        score += 25
        
    b_lower = breathing.lower() if breathing else "normal"
    if "absent" in b_lower:
        score += 50
    elif "labored" in b_lower or "rapid" in b_lower:
        score += 30
        
    s_lower = symptoms.lower() if symptoms else ""
    if "chest pain" in s_lower or "heart attack" in s_lower or "difficulty breathing" in s_lower or "stroke" in s_lower or "severe bleeding" in s_lower:
        score += 35
    elif "fracture" in s_lower or "broken" in s_lower or "burn" in s_lower or "intense pain" in s_lower:
        score += 20
    elif "fever" in s_lower or "cough" in s_lower or "cold" in s_lower:
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
        
    symptoms_list = []
    if symptoms:
        symptoms_list = [s.strip() for s in symptoms.split(",") if s.strip()]
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
        "consciousness": float(40.0 if "alert" not in c_lower else 2.0),
        "breathing": float(45.0 if "normal" not in b_lower else 3.0),
    }

    return {
        "severity_score": int(score),
        "severity_level": level,
        "symptoms_extracted": symptoms_list,
        "assessment": assessment,
        "actions": actions,
        "eta_minutes": 6 if level == "Critical" else 15 if level == "High" else 25 if level == "Moderate" else 45,
        "shap_values": shap
    }

@app.post("/api/triage/image", response_model=TriageImageResponse)
async def triage_image():
    return {"label": "Visible deep cut/bleeding", "confidence": 0.92}

@app.post("/api/triage/voice", response_model=TriageVoiceResponse)
async def triage_voice():
    return {"transcript": "I am feeling dizzy, have a strong chest pain, and cannot breathe properly."}

@app.post("/api/triage", response_model=TriageResponse)
async def triage_assess(req: TriageRequest):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    is_mock = not api_key or api_key.startswith("your_") or api_key.startswith("placeholder") or "key" not in api_key.lower()
    
    if is_mock:
        logger.info("Using mock triage engine (ANTHROPIC_API_KEY is not configured or set to placeholder).")
        return get_mock_triage(
            req.age, req.gender, req.symptoms or "", 
            req.consciousness or "Alert", req.breathing or "Normal",
            req.image_label, req.voice_transcript
        )
        
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=api_key)
        
        prompt = f"""You are an emergency medical AI triage assistant.
Analyze the following patient information:
- Age: {req.age}
- Gender: {req.gender}
- Symptoms description: {req.symptoms}
- Consciousness level: {req.consciousness}
- Breathing pattern: {req.breathing}
- Image analysis findings (if any): {req.image_label}
- Voice transcript of patient (if any): {req.voice_transcript}

Evaluate the severity of the condition.
Return your response ONLY as a valid JSON object matching the following structure:
{{
  "severity_score": <int, 0-100 where 100 is most critical>,
  "severity_level": "<string, one of: 'Critical', 'High', 'Moderate', 'Low'>",
  "symptoms_extracted": [<list of strings representing the key symptoms observed>],
  "assessment": "<string, concise medical triage assessment summarizing why this level was chosen and what key concerns are>",
  "actions": [<list of strings, 3 to 5 clear first-aid or next-step actions in order of priority>],
  "eta_minutes": <int, estimated emergency response arrival time based on severity level, e.g., 5-10 for Critical, 15-20 for High, 30+ for Moderate/Low>,
  "shap_values": {{
     "age": <float, impact value of age on this decision between -50 and 50>,
     "gender": <float, impact value of gender on this decision between -50 and 50>,
     "symptoms": <float, impact value of symptoms on this decision between -50 and 50>,
     "consciousness": <float, impact value of consciousness on this decision between -50 and 50>,
     "breathing": <float, impact value of breathing on this decision between -50 and 50>
  }}
}}
Make sure that your output has NO conversational prefix or suffix, and is pure JSON."""

        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            temperature=0.0,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        data = json.loads(response_text)
        return data
        
    except Exception as e:
        logger.error(f"Error calling Anthropic API, falling back to mock: {e}")
        return get_mock_triage(
            req.age, req.gender, req.symptoms or "", 
            req.consciousness or "Alert", req.breathing or "Normal",
            req.image_label, req.voice_transcript
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
