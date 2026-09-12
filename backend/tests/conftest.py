import pytest
import os
from database import engine, Base
import asyncio

@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    from main import app
    app.dependency_overrides.clear()

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    is_sqlite = "sqlite" in os.getenv("DATABASE_URL", "")
    
    if is_sqlite:
        print("\n[conftest] SQLite detected. Running Base.metadata.create_all for fast tests.")
        async def init_db():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        asyncio.run(init_db())
    else:
        print("\n[conftest] PostgreSQL detected. Relying on Alembic migrations. Ensure you have run 'alembic upgrade head'.")
        # In PostgreSQL, we assume Alembic migrations have already been run.

    yield
