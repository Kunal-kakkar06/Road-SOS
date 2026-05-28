from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import httpx, os, jwt

from database import get_db
from models.medical_profile import MedicalProfile

router = APIRouter(prefix="/api/digilocker", tags=["DigiLocker"])

DIGILOCKER_CLIENT_ID     = os.getenv("DIGILOCKER_CLIENT_ID")
DIGILOCKER_CLIENT_SECRET = os.getenv("DIGILOCKER_CLIENT_SECRET")
DIGILOCKER_REDIRECT_URI  = os.getenv("DIGILOCKER_REDIRECT_URI",
                            "http://localhost:5173/digilocker/callback")
SECRET = os.getenv("JWT_SECRET", "roadsos-dev-secret")


def get_user(authorization: str = None) -> str:
    if not authorization: raise HTTPException(401, "Not authenticated")
    token   = authorization.split(" ")[1]
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    return payload["user_id"]


# ── GET /api/digilocker/auth-url ──────────────────────────────
# Frontend calls this to get the OAuth2 redirect URL
@router.get("/auth-url")
def get_auth_url(redirect_uri: Optional[str] = Query(None)):
    if not DIGILOCKER_CLIENT_ID or DIGILOCKER_CLIENT_ID == "your_client_id":
        # Mock mode fallback for local sandbox trials - redirect to interactive mock DigiLocker interface!
        fallback_uri = redirect_uri or "http://localhost:5175/digilocker/callback"
        import urllib.parse
        parsed_uri = urllib.parse.urlparse(fallback_uri)
        base_origin = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
        mock_redirect = f"{base_origin}/mock-digilocker?redirect_uri={urllib.parse.quote(fallback_uri)}"
        return {"auth_url": mock_redirect}
        
    base = "https://api.digitallocker.gov.in/public/oauth2/1/authorize"
    params = (
        f"?response_type=code"
        f"&client_id={DIGILOCKER_CLIENT_ID}"
        f"&redirect_uri={DIGILOCKER_REDIRECT_URI}"
        f"&state=roadsos_medical"
        f"&scope=r_HLTHRCD"   # ABHA Health Record scope
    )
    return {"auth_url": base + params}


from pydantic import BaseModel

class CallbackPayload(BaseModel):
    code: str

# ── POST /api/digilocker/callback ─────────────────────────────
# Called after user authorises — exchange code for token + fetch ABHA
@router.post("/callback")
async def digilocker_callback(
    payload:       CallbackPayload,
    authorization: str  = None,
    db:            Session = Depends(get_db),
):
    code = payload.code
    try:
        user_id = get_user(authorization)
    except Exception:
        # Development fallback
        user_id = "anonymous"

    # 1. Exchange code for access token (Bypass real API query if mock trial)
    if "mock_digilocker" in code or not DIGILOCKER_CLIENT_ID or DIGILOCKER_CLIENT_ID == "your_client_id":
        parsed = parse_abha_record("")
        return {
            "success":    True,
            "abha_id":    parsed.get("abha_id"),
            "prefilled":  parsed,
            "message":    "DigiLocker data imported. Review and save your profile.",
        }

    async with httpx.AsyncClient() as client:

        # 2. Fetch ABHA health record
        health_res = await client.get(
            "https://api.digitallocker.gov.in/public/oauth2/1/xml/HLTHRCD",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    # 3. Parse XML health record → extract fields
    # (In production use xml.etree.ElementTree to parse ABHA XML)
    # For prototype return mock-parsed data:
    parsed = parse_abha_record(health_res.text)

    # 4. Update DB profile with DigiLocker data
    profile = db.query(MedicalProfile).filter(
        MedicalProfile.user_id == user_id
    ).first()
    if profile:
        profile.digilocker_linked = True
        profile.abha_id           = parsed.get("abha_id")
        # Only pre-fill fields that are empty — don't overwrite user data
        if not profile.blood_type:   profile.blood_type  = parsed.get("blood_type")
        if not profile.allergies:    profile.allergies   = parsed.get("allergies", [])
        if not profile.conditions:   profile.conditions  = parsed.get("conditions", [])
        if not profile.medications:  profile.medications = parsed.get("medications", [])
        db.commit()

    return {
        "success":    True,
        "abha_id":    parsed.get("abha_id"),
        "prefilled":  parsed,
        "message":    "DigiLocker data imported. Review and save your profile.",
    }


def parse_abha_record(xml_text: str) -> dict:
    """
    Parse ABHA XML health record.
    In prototype — returns mock data for UI testing.
    Replace with real XML parsing using xml.etree.ElementTree in production.
    """
    return {
        "abha_id":    "12-3456-7890-1234",
        "blood_type": "B+",
        "allergies":  ["Penicillin"],
        "conditions": ["Hypertension"],
        "medications":["Metformin 500mg"],
    }
