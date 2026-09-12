import asyncio
from fastapi.testclient import TestClient
from main import app
from dependencies.auth_deps import require_user
from ai.schemas.input_schema import AIInput
from routers.triage import TriageRequest
from ai.feature_engine.feature_builder import FeatureBuilder
from ai.models.severity_model import get_severity_model
from ai.feature_engine.nlp_service import extract_features
from services.fusion_triage import _build_features

app.dependency_overrides[require_user] = lambda: type("User", (), {"uuid": "test-user-123", "role": "USER"})()
client = TestClient(app)

print("\n--- ISSUE 1: Breathing Regression Tests ---")
breathing_phrases = [
    "Severe difficulty breathing, gasping.",
    "I can't breathe.",
    "I am struggling to breathe."
]

for p in breathing_phrases:
    f = extract_features(p)
    print(f"Phrase: '{p}' -> Score: {f.nlp_severity_score}, Breathing Ind: {f.breathing_difficulty_indicator}, Serious: {f.serious_keyword_count}")
    assert f.nlp_severity_score >= 0.7
    assert f.breathing_difficulty_indicator > 0

print("\n--- ISSUES 2 & 3: Image & Sensor Signal Propagation Tests ---")
scenarios = [
    {"name": "4. Deep bleeding wound", "payload": {"text": "I have a deep bleeding wound."}},
    {"name": "5. Unconscious + not breathing", "payload": {"text": "Someone is unconscious and not breathing."}},
    {"name": "6. Vehicle collision, trapped, fire", "payload": {"text": "Vehicle collision, person trapped, fire present."}},
    {"name": "7. text only", "payload": {"text": "Fractured arm"}},
    {"name": "8. text + image", "payload": {"text": "Fractured arm", "has_image": True, "image_score": 0.85}},
    {"name": "9. text + sensor", "payload": {"text": "Chest pain", "sensor_score": 0.90}},
    {"name": "10. text + image + sensor", "payload": {"text": "Severe crash", "image_score": 0.95, "sensor_score": 0.90}},
    {"name": "11. minimal request", "payload": {}}
]

for s in scenarios:
    print(f"\nScenario {s['name']}: {s['payload']}")
    
    # Run through router
    resp = client.post("/api/triage", json=s['payload'])
    assert resp.status_code == 200
    
    # Also run internals to dump exact feature vector
    req = TriageRequest(**s['payload'])
    combined_symptoms = (req.text or req.symptoms) or ""
    ai_in = AIInput(
        request_id="test",
        symptoms=combined_symptoms.strip() or None,
        has_image=bool(req.has_image or req.image_label or req.image_score is not None),
        image_label=req.image_label,
        image_score=req.image_score,
        has_sensor_data=bool(req.sensor_score is not None),
        sensor_score=req.sensor_score,
    )
    
    fv = FeatureBuilder().build(ai_in)
    model = get_severity_model()
    pred = model.predict(fv)
    
    img = fv.image.image_severity_score if fv.image.image_available else 0.5
    nlp = fv.audio.nlp_severity_score if fv.audio.audio_available else None
    if nlp is None and fv.text.raw_text_available:
        nlp = fv.text.nlp_severity_score
    nlp = nlp if nlp is not None else 0.5
    sen = fv.sensor_score if fv.sensor_available else 0.5
    risk = fv.patient.medical_risk_score or 0.5
    has_img = fv.image.image_available
    has_nlp = fv.text.raw_text_available
    has_sen = fv.sensor_available
    mean_s = (img + nlp + sen) / 3
    max_s = max(img, nlp, sen)
    c_s = float(has_img) + float(has_nlp) + float(has_sen)
    
    vec = [img, nlp, sen, risk, float(has_img), float(has_nlp), float(has_sen), mean_s, max_s, c_s]
    
    print(f"NLP Score: {nlp}")
    print(f"FeatureVector Image Available: {fv.image.image_available}, Image Score: {fv.image.image_severity_score}")
    print(f"FeatureVector Sensor Available: {fv.sensor_available}, Sensor Score: {fv.sensor_score}")
    print(f"Exact 10-feature array: {vec}")
    print(f"XGBoost probabilities: {pred.class_probabilities}")
    print(f"Predicted class: {pred.severity_class.name}")
    print(f"Confidence (Severity Score %): {pred.confidence}")
    print(f"SHAP: {[(x.feature, round(x.impact, 4)) for x in pred.shap_factors]}")

