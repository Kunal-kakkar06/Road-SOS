import asyncio
import sys
import os

# Adjust path so we can import database and models from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import engine, AsyncSessionLocal, Base
from models import FIRTemplate
from sqlalchemy.future import select

KARNATAKA_STEPS = [
    {
        "step_number": 1,
        "title": "Access e-FIR Online portal or Visit Station",
        "description": "Log onto the Karnataka State Police (KSP) App/Citizen Portal, or locate the nearest police station relative to the crash location."
    },
    {
        "step_number": 2,
        "title": "Submit Incident Telemetry Report",
        "description": "Provide the official RoadSOS Incident PDF report containing exact collision coordinates, speed at impact, and emergency ambulance dispatch records as verified evidence."
    },
    {
        "step_number": 3,
        "title": "Register Vehicle Details",
        "description": "Input vehicle registration registration certificate (RC), drivers license details of all parties involved, and insurance policy coverage cards."
    },
    {
        "step_number": 4,
        "title": "Declare Witness Statements",
        "description": "Log contact numbers and testimonies of nearby witnesses. Make sure to specify any traffic indicators or road conditions."
    },
    {
        "step_number": 5,
        "title": "Obtain Signed Copy (Section 154 CrPC)",
        "description": "Ask for your free certified copy of the recorded FIR immediately at the desk, required for initiating third-party insurance claims."
    }
]

async def seed_fir():
    # Database schema is now managed by Alembic.

    async with AsyncSessionLocal() as db:
        # Check if template already exists
        result = await db.execute(select(FIRTemplate).filter(FIRTemplate.state == "Karnataka"))
        existing = result.scalars().first()
        if existing:
            print("Karnataka FIR template already exists, updating...")
            existing.steps = KARNATAKA_STEPS
        else:
            print("Creating Karnataka FIR template...")
            template = FIRTemplate(
                state="Karnataka",
                steps=KARNATAKA_STEPS
            )
            db.add(template)
        
        # Add Maharashtra for state guidelines choice
        result_mh = await db.execute(select(FIRTemplate).filter(FIRTemplate.state == "Maharashtra"))
        existing_mh = result_mh.scalars().first()
        mh_steps = KARNATAKA_STEPS.copy()
        mh_steps[0] = {
            "step_number": 1,
            "title": "Register on Maharashtra Police Citizen Portal",
            "description": "Create an account on the Maharashtra Police citizen portal or present in-person at the local jurisdiction station."
        }
        if existing_mh:
            existing_mh.steps = mh_steps
        else:
            db.add(FIRTemplate(state="Maharashtra", steps=mh_steps))

        await db.commit()
        print("Seeded FIR templates successfully.")

if __name__ == "__main__":
    asyncio.run(seed_fir())
