"""
In-memory hospital database for prototype.
No PostgreSQL/PostGIS needed — uses haversine for geo queries.
Real production: swap this with a PostGIS-backed model.
"""
import uuid
import copy
from datetime import datetime

BENGALURU_HOSPITALS = [
    {
        "id": str(uuid.uuid4()),
        "name": "Manipal Hospital, Old Airport Road",
        "address": "98, HAL Airport Rd, Kodihalli, Bengaluru, 560017",
        "phone": "+918067999999",
        "type": "private",
        "latitude": 12.9597,
        "longitude": 77.6484,
        "trauma_beds_total": 20,
        "trauma_beds_available": 8,
        "icu_beds_total": 40,
        "icu_beds_available": 12,
        "general_beds_available": 45,
        "blood_bank": True,
        "blood_types_available": ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"],
        "has_trauma_center": True,
        "has_cath_lab": True,
        "has_neuro_unit": True,
        "is_active": True,
        "beds_updated_at": datetime.utcnow().isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Apollo Hospital, Bannerghatta Road",
        "address": "154/11, Bannerghatta Rd, Opp IIM-B, Bengaluru, 560076",
        "phone": "+918026304050",
        "type": "private",
        "latitude": 12.8939,
        "longitude": 77.5969,
        "trauma_beds_total": 15,
        "trauma_beds_available": 5,
        "icu_beds_total": 30,
        "icu_beds_available": 8,
        "general_beds_available": 60,
        "blood_bank": True,
        "blood_types_available": ["A+", "B+", "O+", "AB+", "O-"],
        "has_trauma_center": True,
        "has_cath_lab": True,
        "has_neuro_unit": True,
        "is_active": True,
        "beds_updated_at": datetime.utcnow().isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Victoria Hospital (Govt)",
        "address": "Fort Rd, Krishna Rajendra Market, Bengaluru, 560002",
        "phone": "+918022975201",
        "type": "govt",
        "latitude": 12.9625,
        "longitude": 77.5760,
        "trauma_beds_total": 30,
        "trauma_beds_available": 14,
        "icu_beds_total": 20,
        "icu_beds_available": 6,
        "general_beds_available": 100,
        "blood_bank": True,
        "blood_types_available": ["A+", "A-", "B+", "B-", "O+", "O-", "AB+"],
        "has_trauma_center": True,
        "has_cath_lab": False,
        "has_neuro_unit": True,
        "is_active": True,
        "beds_updated_at": datetime.utcnow().isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Fortis Hospital, Cunningham Road",
        "address": "14, Cunningham Rd, Vasanth Nagar, Bengaluru, 560052",
        "phone": "+918066214444",
        "type": "private",
        "latitude": 12.9897,
        "longitude": 77.5979,
        "trauma_beds_total": 10,
        "trauma_beds_available": 3,
        "icu_beds_total": 25,
        "icu_beds_available": 7,
        "general_beds_available": 30,
        "blood_bank": True,
        "blood_types_available": ["A+", "B+", "O+", "AB+"],
        "has_trauma_center": True,
        "has_cath_lab": True,
        "has_neuro_unit": False,
        "is_active": True,
        "beds_updated_at": datetime.utcnow().isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Bowring & Lady Curzon Hospital (Govt)",
        "address": "Shivaji Nagar, Bengaluru, 560001",
        "phone": "+918025320690",
        "type": "govt",
        "latitude": 12.9795,
        "longitude": 77.6082,
        "trauma_beds_total": 25,
        "trauma_beds_available": 10,
        "icu_beds_total": 15,
        "icu_beds_available": 4,
        "general_beds_available": 80,
        "blood_bank": False,
        "blood_types_available": [],
        "has_trauma_center": True,
        "has_cath_lab": False,
        "has_neuro_unit": False,
        "is_active": True,
        "beds_updated_at": datetime.utcnow().isoformat(),
    },
]


def get_all_hospitals():
    """Return a deep copy of all active hospitals."""
    return [copy.deepcopy(h) for h in BENGALURU_HOSPITALS if h["is_active"]]


def get_hospital_by_id(hospital_id: str):
    """Find a hospital by its UUID string."""
    for h in BENGALURU_HOSPITALS:
        if h["id"] == hospital_id:
            return h
    return None


def update_hospital_beds(hospital_id: str, **kwargs):
    """Update bed counts for a hospital in memory."""
    h = get_hospital_by_id(hospital_id)
    if not h:
        return None
    if "trauma_beds" in kwargs and kwargs["trauma_beds"] is not None:
        h["trauma_beds_available"] = kwargs["trauma_beds"]
    if "icu_beds" in kwargs and kwargs["icu_beds"] is not None:
        h["icu_beds_available"] = kwargs["icu_beds"]
    if "general_beds" in kwargs and kwargs["general_beds"] is not None:
        h["general_beds_available"] = kwargs["general_beds"]
    if "blood_types" in kwargs and kwargs["blood_types"] is not None:
        h["blood_types_available"] = kwargs["blood_types"]
    h["beds_updated_at"] = datetime.utcnow().isoformat()
    return h
