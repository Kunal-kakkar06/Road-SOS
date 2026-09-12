import pytest
import asyncio
from fastapi.testclient import TestClient
from main import app
from dependencies.auth_deps import require_user
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from sqlalchemy import select
from models.triage_model import TriageEvent

client = TestClient(app)

@pytest.mark.asyncio
async def test_triage_history_persistence():
    app.dependency_overrides[require_user] = lambda: type("User", (), {"uuid": "test-hist-usr", "role": "USER"})()
    
    # Clear existing
    async with AsyncSessionLocal() as db:
        await db.execute(TriageEvent.__table__.delete().where(TriageEvent.user_id == "test-hist-usr"))
        await db.commit()
    
    # Run a sync triage
    payload = {"text": "broken arm and severe pain", "age": 25}
    resp = client.post("/api/triage", json=payload)
    assert resp.status_code == 200
    
    # Check history endpoint
    hist_resp = client.get("/api/triage/history")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert len(hist_data) == 1
    assert hist_data[0]["final_severity"] in ["Critical", "High", "Moderate", "Low"]
    
    # Check db directly
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(TriageEvent).where(TriageEvent.user_id == "test-hist-usr"))
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].transcript is None
        assert events[0].final_severity == hist_data[0]["final_severity"]
        
    app.dependency_overrides.clear()

