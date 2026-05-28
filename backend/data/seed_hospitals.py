from sqlalchemy.orm import Session
from database import engine, Base, AsyncSessionLocal
from models.hospital_model import Hospital
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
import asyncio

BENGALURU_HOSPITALS = [
    {
        "name": "Manipal Hospital, Old Airport Road",
        "address": "98, HAL Airport Rd, Kodihalli, Bengaluru, 560017",
        "phone": "+918067999999",
        "type": "private",
        "lat": 12.9597, "lng": 77.6484,
        "trauma_beds_total": 20, "trauma_beds_available": 8,
        "icu_beds_total": 40,    "icu_beds_available": 12,
        "general_beds_available": 45,
        "blood_bank": True,
        "blood_types_available": ["A+","A-","B+","B-","O+","O-","AB+","AB-"],
        "has_trauma_center": True, "has_cath_lab": True, "has_neuro_unit": True,
    },
    {
        "name": "Apollo Hospital, Bannerghatta Road",
        "address": "154/11, Bannerghatta Rd, Opp IIM-B, Bengaluru, 560076",
        "phone": "+918026304050",
        "type": "private",
        "lat": 12.8939, "lng": 77.5969,
        "trauma_beds_total": 15, "trauma_beds_available": 5,
        "icu_beds_total": 30,    "icu_beds_available": 8,
        "general_beds_available": 60,
        "blood_bank": True,
        "blood_types_available": ["A+","B+","O+","AB+","O-"],
        "has_trauma_center": True, "has_cath_lab": True, "has_neuro_unit": True,
    },
    {
        "name": "Victoria Hospital (Govt)",
        "address": "Fort Rd, Krishna Rajendra Market, Bengaluru, 560002",
        "phone": "+918022975201",
        "type": "govt",
        "lat": 12.9625, "lng": 77.5760,
        "trauma_beds_total": 30, "trauma_beds_available": 14,
        "icu_beds_total": 20,    "icu_beds_available": 6,
        "general_beds_available": 100,
        "blood_bank": True,
        "blood_types_available": ["A+","A-","B+","B-","O+","O-","AB+"],
        "has_trauma_center": True, "has_cath_lab": False, "has_neuro_unit": True,
    },
    {
        "name": "Fortis Hospital, Cunningham Road",
        "address": "14, Cunningham Rd, Vasanth Nagar, Bengaluru, 560052",
        "phone": "+918066214444",
        "type": "private",
        "lat": 12.9897, "lng": 77.5979,
        "trauma_beds_total": 10, "trauma_beds_available": 3,
        "icu_beds_total": 25,    "icu_beds_available": 7,
        "general_beds_available": 30,
        "blood_bank": True,
        "blood_types_available": ["A+","B+","O+","AB+"],
        "has_trauma_center": True, "has_cath_lab": True, "has_neuro_unit": False,
    },
    {
        "name": "Bowring & Lady Curzon Hospital (Govt)",
        "address": "Shivaji Nagar, Bengaluru, 560001",
        "phone": "+918025320690",
        "type": "govt",
        "lat": 12.9795, "lng": 77.6082,
        "trauma_beds_total": 25, "trauma_beds_available": 10,
        "icu_beds_total": 15,    "icu_beds_available": 4,
        "general_beds_available": 80,
        "blood_bank": False,
        "blood_types_available": [],
        "has_trauma_center": True, "has_cath_lab": False, "has_neuro_unit": False,
    },
]

async def seed():
    # Make sure tables are created
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"Metadata creation warning (normal if SQLite/non-PostGIS): {e}")

        
    async with AsyncSessionLocal() as db:
        # Clear existing using execute
        from sqlalchemy import delete
        await db.execute(delete(Hospital))
        await db.commit()

        import os
        is_sqlite = "sqlite" in os.getenv("DATABASE_URL", "")
        for h in BENGALURU_HOSPITALS:
            hospital = Hospital(
                name         = h["name"],
                address      = h["address"],
                phone        = h.get("phone"),
                type         = h["type"],
                location     = None if is_sqlite else from_shape(Point(h["lng"], h["lat"]), srid=4326),
                latitude     = h["lat"],
                longitude    = h["lng"],
                trauma_beds_total     = h["trauma_beds_total"],
                trauma_beds_available = h["trauma_beds_available"],
                icu_beds_total        = h["icu_beds_total"],
                icu_beds_available    = h["icu_beds_available"],
                general_beds_available= h["general_beds_available"],
                blood_bank            = h["blood_bank"],
                blood_types_available = h["blood_types_available"],
                has_trauma_center     = h["has_trauma_center"],
                has_cath_lab          = h["has_cath_lab"],
                has_neuro_unit        = h["has_neuro_unit"],
            )
            db.add(hospital)

        await db.commit()
        print(f"Seeded {len(BENGALURU_HOSPITALS)} hospitals.")

if __name__ == "__main__":
    asyncio.run(seed())
