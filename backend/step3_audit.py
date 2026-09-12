import asyncio
import json
from ai.schemas.input_schema import AIInput
from routers.triage import TriageRequest
from ai.feature_engine.feature_builder import FeatureBuilder
from ai.models.severity_model import get_severity_model
from ai.decision.emergency_decision import EmergencyDecisionEngine
from services.fusion_triage import _build_features, FEATURE_NAMES
from ai.feature_engine.nlp_service import extract_features

print("--- NEGATION AUDIT ---")
negation_phrases = [
    "I am having chest pain.",
    "I am NOT having chest pain.",
    "My chest pain has subsided.",
    "I don't have difficulty breathing.",
    "I am not unconscious."
]

for p in negation_phrases:
    feat = extract_features(p)
    print(f"\nPhrase: '{p}'")
    print(f"Chest Pain Ind: {feat.chest_pain_indicator}")
    print(f"Breathing Diff Ind: {feat.breathing_difficulty_indicator}")
    print(f"Unconscious Ind: {feat.unconsciousness_indicator}")
    print(f"NLP Score: {feat.nlp_severity_score}")

print("\n--- FEATURE EXTRACTION AUDIT ---")
audit_phrases = {
    "A": "I am unconscious and not breathing.",
    "B": "There was a massive collision and someone is trapped in a burning car!",
    "C": "I have a deep cut and there is significant bleeding.",
    "D": "I have a mild headache.",
    "E": "I feel slightly tired."
}

builder = FeatureBuilder()
model = get_severity_model()
decision_engine = EmergencyDecisionEngine()

for k, v in audit_phrases.items():
    print(f"\nScenario {k}: '{v}'")
    
    req = TriageRequest(text=v)
    combined = (req.text or req.symptoms) or ""
    ai_in = AIInput(request_id="test", symptoms=combined.strip() or None)
    fv = builder.build(ai_in)
    
    print("Structured NLP Features:")
    print(f"  symptom_count: {fv.text.symptom_count}")
    print(f"  emergency_keyword_count: {fv.text.emergency_keyword_count}")
    print(f"  serious_keyword_count: {fv.text.serious_keyword_count}")
    print(f"  moderate_keyword_count: {fv.text.moderate_keyword_count}")
    print(f"  nlp_severity_score: {fv.text.nlp_severity_score}")
    print(f"  bleeding_indicator: {fv.text.bleeding_indicator}")
    print(f"  breathing_difficulty_indicator: {fv.text.breathing_difficulty_indicator}")
    print(f"  unconsciousness_indicator: {fv.text.unconsciousness_indicator}")
    print(f"  trauma_indicator: {fv.text.trauma_indicator}")
    print(f"  fire_indicator: {fv.text.fire_indicator}")
    print(f"  trapped_indicator: {fv.text.trapped_indicator}")
    print(f"  chest_pain_indicator: {fv.text.chest_pain_indicator}")
    print(f"  accident_indicator: {fv.text.accident_indicator}")
    print(f"  pain_severity_indicator: {fv.text.pain_severity_indicator}")
    print(f"  urgency_indicator: {fv.text.urgency_indicator}")

    img = fv.image.image_severity_score if fv.image.image_available else 0.5
    nlp = fv.audio.nlp_severity_score if fv.audio.audio_available else None
    if nlp is None and fv.text.raw_text_available:
        nlp = fv.text.nlp_severity_score
    nlp = nlp if nlp is not None else 0.5
    sen = fv.sensor_score if fv.sensor_available else 0.5
    risk = fv.patient.medical_risk_score or 0.5
    xgb_features = _build_features(img, nlp, sen, risk, fv.image.image_available, fv.text.raw_text_available, fv.sensor_available)
    
    print(f"10-Feature Vector: {xgb_features[0].tolist()}")
