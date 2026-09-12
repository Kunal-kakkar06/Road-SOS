import asyncio
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/api/ai/health")
    assert response.status_code == 200
    data = response.json()
    print("Health:", data)
    assert data["model"]["status"] == "ready"
    assert data["model"]["model_type"] == "xgboost"

def test_emergency():
    payload = {
        "text": "There was a massive collision and someone is trapped in a burning car! Send an ambulance immediately!",
        "latitude": 40.7128,
        "longitude": -74.006,
        "has_voice": False,
        "has_image": False,
        "medical_profile": {
            "age": 45,
            "pre_existing_conditions": ["hypertension"]
        }
    }
    
    # We bypass auth by injecting a mock dependency or depending on how it's implemented.
    # Actually, in tests/ai/test_xgboost_fallback.py we can see how endpoints are tested. 
    # Let's just override the auth dependency.
    from dependencies.auth_deps import require_user
    app.dependency_overrides[require_user] = lambda: type("User", (), {"uuid": "test-user-123", "role": "USER"})()

    response = client.post(
        "/api/triage",
        json=payload
    )
    
    print("\nAPI Response:", response.status_code)
    try:
        data = response.json()
        print(data)
    except:
        print(response.text)
        
    assert response.status_code == 200
    assert data["severity_level"] in ["High", "Critical"]
    
if __name__ == "__main__":
    test_health()
    test_emergency()
