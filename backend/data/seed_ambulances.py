import asyncio
from database import engine, Base, AsyncSessionLocal
from models.ambulance_provider import AmbulanceProvider
from datetime import datetime
from sqlalchemy import delete

PROVIDERS = [
    {
        "name": "CATS Ambulance — Unit 4",
        "operator_name": "Ravi Kumar",
        "phone": "+919876543001",
        "vehicle_number": "KA01AB1234",
        "type": "als",
        "lat": 12.9716, "lng": 77.5946,   # near MG Road
        "is_verified": True,
    },
    {
        "name": "Apollo Reach Ambulance",
        "operator_name": "Suresh M",
        "phone": "+919876543002",
        "vehicle_number": "KA01CD5678",
        "type": "icu",
        "lat": 12.9352, "lng": 77.6245,   # near Koramangala
        "is_verified": True,
    },
    {
        "name": "Govt 108 Ambulance — BLR North",
        "operator_name": "Mahesh G",
        "phone": "+919876543003",
        "vehicle_number": "KA01EF9012",
        "type": "basic",
        "lat": 13.0298, "lng": 77.5838,   # near Hebbal
        "is_verified": True,
    },
    {
        "name": "Ziqitza 1298 — Unit 7",
        "operator_name": "Anand S",
        "phone": "+919876543004",
        "vehicle_number": "KA01GH3456",
        "type": "als",
        "lat": 12.9139, "lng": 77.6448,   # near HSR Layout
        "is_verified": True,
    },
    {
        "name": "StanPlus Ambulance",
        "operator_name": "Vikram D",
        "phone": "+919876543005",
        "vehicle_number": "KA01IJ7890",
        "type": "icu",
        "lat": 12.9915, "lng": 77.7167,   # near Whitefield
        "is_verified": True,
    },
]

async def seed():
    # Database schema is now managed by Alembic.

    async with AsyncSessionLocal() as db:
        try:
            await db.execute(delete(AmbulanceProvider))
            await db.commit()
        except Exception as e:
            print(f"Skipping clean delete: {e}")
            await db.rollback()

        for p in PROVIDERS:
            provider = AmbulanceProvider(
                name           = p["name"],
                operator_name  = p["operator_name"],
                phone          = p["phone"],
                vehicle_number = p["vehicle_number"],
                type           = p["type"],
                latitude       = p["lat"],
                longitude      = p["lng"],
                is_verified    = p["is_verified"],
                is_available   = True,
                is_active      = True,
                verified_at    = datetime.utcnow(),
                location_updated = datetime.utcnow(),
            )
            db.add(provider)
        await db.commit()
    print(f"Seeded {len(PROVIDERS)} ambulance providers successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
