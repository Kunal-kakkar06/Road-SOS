import asyncio
import datetime
from sqlalchemy.future import select
from database import engine, AsyncSessionLocal, Base
import models

# 10 verified providers in Bengaluru
providers_data = [
    {"name": "Ziqitza Healthcare", "licence_number": "LIC-ZH-001", "contact_phone": "+919876543210"},
    {"name": "StanPlus", "licence_number": "LIC-SP-002", "contact_phone": "+919876543211"},
    {"name": "Medulance", "licence_number": "LIC-MD-003", "contact_phone": "+919876543212"},
    {"name": "Apollo Ambulance", "licence_number": "LIC-AA-004", "contact_phone": "+919876543213"},
    {"name": "Manipal EMS", "licence_number": "LIC-MP-005", "contact_phone": "+919876543214"},
    {"name": "BVG CATS", "licence_number": "LIC-BC-006", "contact_phone": "+919876543215"},
    {"name": "Portea Medical", "licence_number": "LIC-PM-007", "contact_phone": "+919876543216"},
    {"name": "Falck India", "licence_number": "LIC-FI-008", "contact_phone": "+919876543217"},
    {"name": "Medivic", "licence_number": "LIC-MV-009", "contact_phone": "+919876543218"},
    {"name": "GVK EMRI", "licence_number": "LIC-GV-010", "contact_phone": "+919876543219"}
]

# Bengaluru coordinates
locations = [
    {"name": "Koramangala", "lat": 12.9352, "lng": 77.6245},
    {"name": "Whitefield", "lat": 12.9698, "lng": 77.7499},
    {"name": "Hebbal", "lat": 13.0358, "lng": 77.5970},
    {"name": "Indiranagar", "lat": 12.9784, "lng": 77.6408},
    {"name": "Jayanagar", "lat": 12.9250, "lng": 77.5938},
    {"name": "Electronic City", "lat": 12.8399, "lng": 77.6770},
    {"name": "BTM Layout", "lat": 12.9166, "lng": 77.6101}
]

async def seed_data():
    # Database schema is now managed by Alembic.

    async with AsyncSessionLocal() as db:
        # Check if providers already exist to prevent duplicate seedings
        result = await db.execute(select(models.Provider))
        existing_providers = result.scalars().all()
        if existing_providers:
            print("Database already seeded with providers. Skipping seeding.")
            return

        print("Seeding database...")

        # Add providers
        db_providers = []
        for p in providers_data:
            prov = models.Provider(
                name=p["name"],
                licence_number=p["licence_number"],
                licence_expiry=datetime.date(2030, 1, 1),
                is_verified=True,  # Seed verified=True
                contact_phone=p["contact_phone"]
            )
            db.add(prov)
            db_providers.append(prov)
        
        await db.flush()  # populate provider IDs

        # Add 2 ambulances per provider
        ambulance_index = 1
        for i, prov in enumerate(db_providers):
            for j in range(2):
                # Distribute location index sequentially across the 7 regions
                loc_idx = (i * 2 + j) % len(locations)
                loc = locations[loc_idx]
                
                # Add minor jitter to coordinate offsets so they are clustered near but not identical
                noise_lat = ((i * 3 + j * 7) % 10 - 5) * 0.002
                noise_lng = ((i * 7 + j * 3) % 10 - 5) * 0.002

                amb = models.Ambulance(
                    provider_id=prov.id,
                    vehicle_number=f"KA-03-EM-{1000 + ambulance_index}",
                    driver_name=f"Driver {ambulance_index}",
                    driver_phone=f"+9199000{10000 + ambulance_index}",
                    is_available=True,  # Seed available=True
                    current_lat=loc["lat"] + noise_lat,
                    current_lng=loc["lng"] + noise_lng,
                    last_ping=datetime.datetime.now()
                )
                db.add(amb)
                ambulance_index += 1

        await db.commit()
        print("Database seeding completed successfully! 10 verified providers and 20 ambulances added.")

if __name__ == "__main__":
    asyncio.run(seed_data())
