import asyncio
from ai.schemas.input_schema import AIInput
from routers.triage import TriageRequest
from ai.feature_engine.feature_builder import FeatureBuilder
from ai.models.severity_model import get_severity_model
from ai.decision.emergency_decision import EmergencyDecisionEngine
from services.fusion_triage import _build_features, FEATURE_NAMES
import json

async def run_scenario(name, payload_text):
    raw_payload = {
        "text": payload_text,
        "latitude": 40.7128,
        "longitude": -74.0060,
        "has_voice": False,
        "has_image": False,
        "medical_profile": {
            "age": 45,
            "pre_existing_conditions": ["hypertension"]
        }
    }
    
    req = TriageRequest(**raw_payload)
    
    combined_symptoms = (req.text or req.symptoms) or ""
    ai_input = AIInput(
        request_id="test-id",
        symptoms=combined_symptoms.strip() or None,
        age=None,
        gender=req.gender,
        has_voice=False,
        voice_transcript=req.voice_transcript,
        has_image=False,
        image_label=req.image_label,
    )
    
    builder = FeatureBuilder()
    feature_vector = builder.build(ai_input)
    
    model = get_severity_model()
    prediction = model.predict(feature_vector)
    
    img = feature_vector.image.image_severity_score if feature_vector.image.image_available else 0.5
    nlp = feature_vector.audio.nlp_severity_score if feature_vector.audio.audio_available else None
    if nlp is None and feature_vector.text.raw_text_available:
        nlp = feature_vector.text.nlp_severity_score
    nlp = nlp if nlp is not None else 0.5
    sen = feature_vector.sensor_score if feature_vector.sensor_available else 0.5
    risk = feature_vector.patient.medical_risk_score or 0.5
    has_img = feature_vector.image.image_available
    has_nlp = feature_vector.text.raw_text_available
    has_sen = feature_vector.sensor_available
    
    xgb_features = _build_features(img, nlp, sen, risk, has_img, has_nlp, has_sen)
    
    decision_engine = EmergencyDecisionEngine()
    decision = decision_engine.make_decision(prediction)
    
    print(f"\n--- SCENARIO {name} ---")
    print(f"FeatureVector: {json.dumps(feature_vector.dict())}")
    print(f"Exact 10-feature array: {xgb_features[0].tolist()}")
    print(f"XGBoost probabilities: {prediction.class_probabilities}")
    print(f"Predicted class: {prediction.severity_class.name}")
    print(f"Decision Engine result: {decision.priority}")
    print(f"SHAP factors: {[(f.feature, round(f.impact, 4)) for f in prediction.shap_factors]}")

async def run_diagnostic():
    emergency_text = "There was a massive collision and someone is trapped in a burning car! Send an ambulance immediately!"
    await run_scenario("EMERGENCY", emergency_text)
    
    scenarios = {
        "A": "Minor headache and mild discomfort.",
        "B": "I have a deep cut on my arm and there is significant bleeding.",
        "C": "I am unconscious and not breathing.",
        "D": "Vehicle collision, person trapped inside vehicle, fire present.",
        "E": "I feel slightly tired but otherwise okay."
    }
    
    for k, v in scenarios.items():
        await run_scenario(k, v)

asyncio.run(run_diagnostic())
