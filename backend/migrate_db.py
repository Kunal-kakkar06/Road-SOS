import asyncio
from database import engine, Base
# Import all models to register them with Base.metadata
from models.triage_model import TriageJob, TriageEvent
from models.user import User

async def migrate():
    print("Running DB migration...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
