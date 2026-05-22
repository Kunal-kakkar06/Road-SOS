from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import jwt, os

from database import get_db
from schemas import MedicalProfileCreate, MedicalProfileResponse
from models.medical_profile import MedicalProfile

router = APIRouter(prefix="/api/medical-profile", tags=["Medical Profile"])

SECRET = os.getenv("JWT_SECRET", "roadsos-dev-secret")


# ── Simple JWT auth helper ────────────────────────────────────
# Replace with your actual auth system later
def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        token   = authorization.split(" ")[1]
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
        return payload["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── GET /api/medical-profile ──────────────────────────────────
# Fetch current user's profile
@router.get("/", response_model=MedicalProfileResponse)
def get_profile(
    db:      Session = Depends(get_db),
    user_id: str     = Depends(get_current_user),
):
    profile = db.query(MedicalProfile).filter(
        MedicalProfile.user_id == user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# ── POST /api/medical-profile ─────────────────────────────────
# Create profile (first time setup)
@router.post("/", response_model=MedicalProfileResponse, status_code=201)
def create_profile(
    payload: MedicalProfileCreate,
    db:      Session = Depends(get_db),
    user_id: str     = Depends(get_current_user),
):
    existing = db.query(MedicalProfile).filter(
        MedicalProfile.user_id == user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile already exists. Use PUT to update.")

    profile = MedicalProfile(
        user_id              = user_id,
        full_name            = payload.full_name,
        date_of_birth        = payload.date_of_birth,
        gender               = payload.gender,
        phone                = payload.phone,
        blood_type           = payload.blood_type,
        allergies            = payload.allergies or [],
        medications          = payload.medications or [],
        conditions           = payload.conditions or [],
        disabilities         = payload.disabilities or [],
        emergency_contacts   = [c.model_dump() for c in (payload.emergency_contacts or [])],
        insurance_provider   = payload.insurance_provider,
        insurance_policy_no  = payload.insurance_policy_no,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return profile


# ── PUT /api/medical-profile ──────────────────────────────────
# Update existing profile (upsert)
@router.put("/", response_model=MedicalProfileResponse)
def update_profile(
    payload: MedicalProfileCreate,
    db:      Session = Depends(get_db),
    user_id: str     = Depends(get_current_user),
):
    profile = db.query(MedicalProfile).filter(
        MedicalProfile.user_id == user_id
    ).first()

    if not profile:
        # Auto-create if doesn't exist
        return create_profile(payload, db, user_id)

    profile.full_name           = payload.full_name
    profile.date_of_birth       = payload.date_of_birth
    profile.gender              = payload.gender
    profile.phone               = payload.phone
    profile.blood_type          = payload.blood_type
    profile.allergies           = payload.allergies or []
    profile.medications         = payload.medications or []
    profile.conditions          = payload.conditions or []
    profile.disabilities        = payload.disabilities or []
    profile.emergency_contacts  = [c.model_dump() for c in (payload.emergency_contacts or [])]
    profile.insurance_provider  = payload.insurance_provider
    profile.insurance_policy_no = payload.insurance_policy_no

    db.commit()
    db.refresh(profile)
    return profile


# ── DELETE /api/medical-profile ───────────────────────────────
@router.delete("/")
def delete_profile(
    db:      Session = Depends(get_db),
    user_id: str     = Depends(get_current_user),
):
    profile = db.query(MedicalProfile).filter(
        MedicalProfile.user_id == user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.delete(profile)
    db.commit()
    return {"deleted": True}


# ── GET /api/medical-profile/public/{user_id} ─────────────────
# Public endpoint — no auth — for paramedics scanning QR code
@router.get("/public/{user_id}")
def get_public_profile(user_id: str, db: Session = Depends(get_db)):
    profile = db.query(MedicalProfile).filter(
        MedicalProfile.user_id == user_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    # Return only medically critical info — no insurance, no personal details
    return {
        "full_name":   profile.full_name,
        "blood_type":  profile.blood_type,
        "allergies":   profile.allergies,
        "medications": profile.medications,
        "conditions":  profile.conditions,
        "disabilities":profile.disabilities,
        "emergency_contacts": profile.emergency_contacts,
    }
