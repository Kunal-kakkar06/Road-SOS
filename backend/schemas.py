from pydantic import BaseModel, EmailStr
from typing import List, Optional


class Coords(BaseModel):
    lat: float
    lng: float


class MedicalProfile(BaseModel):
    name:       Optional[str]       = "Unknown"
    bloodType:  Optional[str]       = "Unknown"
    allergies:  Optional[List[str]] = []
    conditions: Optional[List[str]] = []
    userId:     Optional[str]       = "anonymous"


class EmergencyContact(BaseModel):
    name:     str
    phone:    str
    relation: Optional[str] = ""


class SOSTriggerRequest(BaseModel):
    eventId:   str
    profile:   MedicalProfile
    contacts:  List[EmergencyContact]
    coords:    Coords
    timestamp: str


class SOSSyncRequest(BaseModel):
    events: List[SOSTriggerRequest]


class SOSResponse(BaseModel):
    success: bool
    eventId: str
    sent:    int
    failed:  int
    message: str

class CrashAnalyseRequest(BaseModel):
    eventId:            str
    userId:             Optional[str]   = "anonymous"
    latitude:           Optional[float] = 0.0
    longitude:          Optional[float] = 0.0
    timestamp:          str
    peak_acceleration:  float
    delta_v:            float
    jerk:               float
    rotation_rate:      float
    impact_duration_ms: float
    pre_event_accel:    float

class ManualCrashRequest(BaseModel):
    eventId:         str
    userId:          Optional[str]   = "anonymous"
    latitude:        Optional[float] = 0.0
    longitude:       Optional[float] = 0.0
    timestamp:       str
    vehicle_speed:   float
    airbag_deployed: bool
    can_move:        bool

class CrashSOSUpdate(BaseModel):
    eventId:       str
    sos_triggered: bool
    cancelled:     bool

from datetime import date, datetime

class EmergencyContactSchema(BaseModel):
    name:     str
    phone:    str
    relation: Optional[str] = ""

class MedicalProfileCreate(BaseModel):
    full_name:           str
    date_of_birth:       Optional[str]  = None
    gender:              Optional[str]  = None
    phone:               Optional[str]  = None
    blood_type:          Optional[str]  = None
    allergies:           Optional[List[str]] = []
    medications:         Optional[List[str]] = []
    conditions:          Optional[List[str]] = []
    disabilities:        Optional[List[str]] = []
    emergency_contacts:  Optional[List[EmergencyContactSchema]] = []
    insurance_provider:  Optional[str]  = None
    insurance_policy_no: Optional[str]  = None

class MedicalProfileResponse(MedicalProfileCreate):
    user_id:            str
    digilocker_linked:  bool
    abha_id:            Optional[str] = None

    class Config:
        from_attributes = True

class CreateIncidentRequest(BaseModel):
    user_id:         str
    sos_event_id:    Optional[str]   = None
    crash_event_id:  Optional[str]   = None
    dispatch_id:     Optional[str]   = None
    latitude:        Optional[float] = None
    longitude:       Optional[float] = None
    severity:        Optional[str]   = None
    speed_at_impact: Optional[float] = None
    medical_profile: Optional[dict]  = None
    hospital_name:   Optional[str]   = None
    ambulance_name:  Optional[str]   = None
    fir_state:       Optional[str]   = "Karnataka"


class AddEventRequest(BaseModel):
    incident_id: str
    event_type:  str
    description: Optional[str] = None
    metadata:    Optional[dict] = None
    timestamp:   Optional[str]  = None


class CreateAlertRequest(BaseModel):
    user_id:        str
    sos_event_id:   Optional[str]  = None
    incident_id:    Optional[str]  = None
    patient_name:   Optional[str]  = None
    severity:       Optional[str]  = "P2"
    latitude:       float
    longitude:      float
    contacts:       List[dict]     # [{name, phone, relation}]


class LocationUpdateRequest(BaseModel):
    session_id:  str
    latitude:    float
    longitude:   float


class UpdateStatusRequest(BaseModel):
    hospital_name:  Optional[str] = None
    ambulance_name: Optional[str] = None
    severity:       Optional[str] = None


# ── Offline SOS Schemas ────────────────────────────────────────

class Coords(BaseModel):
    lat: float
    lng: float


class SOSMedicalProfile(BaseModel):
    name:       Optional[str]       = "Unknown"
    bloodType:  Optional[str]       = "Unknown"
    allergies:  Optional[List[str]] = []
    conditions: Optional[List[str]] = []
    userId:     Optional[str]       = "anonymous"


class EmergencyContact(BaseModel):
    name:     str
    phone:    str
    relation: Optional[str] = ""


class SOSTriggerRequest(BaseModel):
    eventId:   str
    profile:   SOSMedicalProfile
    contacts:  List[EmergencyContact]
    coords:    Coords
    timestamp: str


class SOSSyncRequest(BaseModel):
    events: List[SOSTriggerRequest]


class SOSResponse(BaseModel):
    success: bool
    eventId: str
    sent:    int
    failed:  int
    message: str


# ── Crash Auto-Detection Schemas ────────────────────────────────

class CrashAnalyseRequest(BaseModel):
    eventId:            str
    userId:             Optional[str]   = "anonymous"
    latitude:           Optional[float] = 0.0
    longitude:          Optional[float] = 0.0
    timestamp:          str
    peak_acceleration:  float
    delta_v:            float
    jerk:               float
    rotation_rate:      float
    impact_duration_ms: float
    pre_event_accel:    float


class ManualCrashRequest(BaseModel):
    eventId:         str
    userId:          Optional[str]   = "anonymous"
    latitude:        Optional[float] = 0.0
    longitude:       Optional[float] = 0.0
    timestamp:       str
    vehicle_speed:   float
    airbag_deployed: bool
    can_move:        bool


class CrashSOSUpdate(BaseModel):
    eventId:       str
    sos_triggered: bool
    cancelled:     bool


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    confirm_password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str  # maps to User.uuid
    email: str
    name: str
    role: str

    class Config:
        orm_mode = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserRoleUpdate(BaseModel):
    role: str


class UserStatusUpdate(BaseModel):
    is_active: bool


class AdminUserResponse(BaseModel):
    id: str  # maps to user uuid
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


class SystemStatsResponse(BaseModel):
    total_users: int
    total_responders: int
    active_users: int
    sos_requests: int
    ai_requests: int
    hospital_searches: int


class ResponderEmergencyStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


