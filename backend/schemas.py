from pydantic import BaseModel
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
