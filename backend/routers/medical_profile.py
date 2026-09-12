from fastapi import APIRouter, Depends, HTTPException, Header
from dependencies.auth_deps import require_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
import jwt, os

from database import get_db
from schemas import MedicalProfileCreate, MedicalProfileResponse
from models.medical_profile import MedicalProfile

router = APIRouter(prefix="/api/medical-profile", tags=["Medical Profile"])

SECRET = os.getenv("JWT_SECRET", "roadsos-super-secret-key-change-in-production")


# ── Simple JWT auth helper ────────────────────────────────────
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
@router.get("/", response_model=MedicalProfileResponse)
async def get_profile(
    db:      AsyncSession = Depends(get_db),
    user_id: str          = Depends(get_current_user),
    _rbac                 = Depends(require_user),
):
    result = await db.execute(select(MedicalProfile).filter(MedicalProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


# ── POST /api/medical-profile ─────────────────────────────────
@router.post("/", response_model=MedicalProfileResponse, status_code=201)
async def create_profile(
    payload: MedicalProfileCreate,
    db:      AsyncSession = Depends(get_db),
    user_id: str          = Depends(get_current_user),
    _rbac                 = Depends(require_user),
):
    result = await db.execute(select(MedicalProfile).filter(MedicalProfile.user_id == user_id))
    existing = result.scalars().first()
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
    await db.commit()
    await db.refresh(profile)

    return profile


# ── PUT /api/medical-profile ──────────────────────────────────
@router.put("/", response_model=MedicalProfileResponse)
async def update_profile(
    payload: MedicalProfileCreate,
    db:      AsyncSession = Depends(get_db),
    user_id: str          = Depends(get_current_user),
    _rbac                 = Depends(require_user),
):
    result = await db.execute(select(MedicalProfile).filter(MedicalProfile.user_id == user_id))
    profile = result.scalars().first()

    if not profile:
        # Auto-create if doesn't exist
        return await create_profile(payload, db, user_id)

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

    await db.commit()
    await db.refresh(profile)
    return profile


# ── DELETE /api/medical-profile ───────────────────────────────
@router.delete("/")
async def delete_profile(
    db:      AsyncSession = Depends(get_db),
    user_id: str          = Depends(get_current_user),
    _rbac                 = Depends(require_user),
):
    result = await db.execute(select(MedicalProfile).filter(MedicalProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.delete(profile)
    await db.commit()
    return {"deleted": True}


# ── GET /api/medical-profile/public/{user_id} ─────────────────
@router.get("/public/{user_id}")
async def get_public_profile(user_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MedicalProfile).filter(MedicalProfile.user_id == user_id))
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {
        "full_name":   profile.full_name,
        "blood_type":  profile.blood_type,
        "allergies":   profile.allergies,
        "medications": profile.medications,
        "conditions":  profile.conditions,
        "disabilities":profile.disabilities,
        "emergency_contacts": profile.emergency_contacts,
    }
