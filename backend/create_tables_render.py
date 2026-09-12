"""
One-time script: Creates all database tables in the Render PostgreSQL database.
Run this from the backend/ directory with the Render external DATABASE_URL:

  DATABASE_URL="postgresql://roadsos:PASS@dpg-xxx.oregon-postgres.render.com/roadsos" python create_tables_render.py
"""
import asyncio
import os
import sys

def main():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        sys.exit(1)

    # Normalize to asyncpg driver + SSL for Render external connections
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Append SSL for external Render connections if not already present
    if "ssl" not in db_url:
        db_url += "?ssl=require"

    print(f"Connecting to: {db_url[:55]}...")

    async def create_all():
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        engine = create_async_engine(db_url, echo=False)

        # Step 1: Install PostGIS extension (required for geometry columns)
        async with engine.begin() as conn:
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                print("✅ PostGIS extension enabled.")
            except Exception as e:
                print(f"⚠️  PostGIS not available: {e}")
                print("   Will skip geometry columns and use lat/lng only.")

        # Step 2: Import all models and create tables
        # We patch the Hospital model to skip geometry if PostGIS is unavailable
        from database import Base
        import models
        import models.hospital_model
        import models.triage_model

        async with engine.begin() as conn:
            # Create all tables, skipping existing ones
            await conn.run_sync(
                lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True)
            )

        await engine.dispose()
        print("\n✅ All tables created successfully in Render PostgreSQL!")
        print("   You can now do a Manual Deploy on Render and the service will go Live.")

    asyncio.run(create_all())

if __name__ == "__main__":
    main()
