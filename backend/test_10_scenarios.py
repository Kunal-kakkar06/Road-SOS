import asyncio
from fastapi.testclient import TestClient
from main import app
from dependencies.auth_deps import require_user

app.dependency_overrides[require_user] = lambda: type("User", (), {"uuid": "test-user-123", "role": "USER"})()
client = TestClient(app)

print("\n--- HEALTH CHECK ---")
resp = client.get("/api/ai/health")
print(resp.json())

scenarios = [
    {"name": "1. Minor headache", "payload": {"text": "Minor headache."}},
    {"name": "2. Mild fatigue", "payload": {"text": "Mild fatigue and slightly tired."}},
    {"name": "3. Deep bleeding wound", "payload": {"text": "Deep bleeding wound, blood everywhere."}},
    {"name": "4. Severe breathing difficulty", "payload": {"text": "Severe difficulty breathing, gasping."}},
    {"name": "5. Unconscious + not breathing", "payload": {"text": "Unconscious and not breathing."}},
    {"name": "6. Vehicle collision + trapped person + fire", "payload": {"text": "Vehicle collision, trapped person, on fire."}},
    {"name": "7. Text + image", "payload": {"text": "Broken bone.", "has_image": True, "image_label": "fracture"}},
    {"name": "8. Text + sensor", "payload": {"text": "Chest pain.", "has_sensor": True}},
    {"name": "9. Text + image + sensor", "payload": {"text": "Severe crash.", "has_image": True, "image_label": "collision", "has_sensor": True}},
    {"name": "10. Minimal request", "payload": {}},
]

for s in scenarios:
    print(f"\n--- SCENARIO {s['name']} ---")
    resp = client.post("/api/triage", json=s['payload'])
    if resp.status_code != 200:
        print("ERROR", resp.text)
        continue
        
    data = resp.json()
    print("Severity Score:", data.get("severity_score"))
    print("Severity Level:", data.get("severity_level"))
    print("Decision Priority:", data.get("assessment"))
    if "shap_values" in data:
        print("SHAP:", data["shap_values"])
    
    # We also need to report XGBoost probabilities, exact feature vector, and NLP score.
    # To get those, let's run the internal pipeline too.
    from ai.schemas.input_schema import AIInput
    from routers.triage import TriageRequest
    from ai.feature_engine.feature_builder import FeatureBuilder
    from ai.models.severity_model import get_severity_model
    from services.fusion_triage import _build_features
    
    req = TriageRequest(**s['payload'])
    combined_symptoms = (req.text or req.symptoms) or ""
    ai_in = AIInput(
        request_id="test",
        symptoms=combined_symptoms.strip() or None,
        has_image=bool(req.has_image or req.image_label),
        image_label=req.image_label,
        # Hack to simulate sensor presence for the test
    )
    # the feature builder doesn't know about sensor data directly from AIInput unless we set has_sensor_data, but AIInput has has_sensor_data=False by default.
    # Let's set it manually
    if s["payload"].get("has_sensor"):
        ai_in.has_sensor_data = True
        
    fv = FeatureBuilder().build(ai_in)
    model = get_severity_model()
    pred = model.predict(fv)
    
    img = fv.image.image_severity_score if fv.image.image_available else 0.5
    nlp = fv.audio.nlp_severity_score if fv.audio.audio_available else None
    if nlp is None and fv.text.raw_text_available:
        nlp = fv.text.nlp_severity_score
    nlp = nlp if nlp is not None else 0.5
    sen = 0.8 if s["payload"].get("has_sensor") else (fv.sensor_score if fv.sensor_available else 0.5) # Hardcode mock sensor
    risk = fv.patient.medical_risk_score or 0.5
    
    has_img = fv.image.image_available
    has_nlp = fv.text.raw_text_available
    has_sen = s["payload"].get("has_sensor", False)
    
    mean_s = (img + nlp + sen) / 3
    max_s = max(img, nlp, sen)
    c_s = float(has_img) + float(has_nlp) + float(has_sen)
    
    print(f"NLP Score: {nlp}")
    print(f"10-Feature Vector: {[img, nlp, sen, risk, float(has_img), float(has_nlp), float(has_sen), mean_s, max_s, c_s]}")
    print(f"Probabilities: {pred.class_probabilities}")
