from fastapi.testclient import TestClient
from main import app
from dependencies.auth_deps import require_user
import json

def override_require_user():
    return {"id": 1, "role": "USER", "email": "test@roadsos.com"}

app.dependency_overrides[require_user] = override_require_user

client = TestClient(app)

response = client.post("/api/triage/image")
print(f"Status Code: {response.status_code}")
print(json.dumps(response.json(), indent=2))
