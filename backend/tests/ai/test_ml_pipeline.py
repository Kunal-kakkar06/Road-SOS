import pytest
from ai.models.severity_model import get_severity_model
from routers.triage import TriageRequest
from ai.schemas.input_schema import AIInput
from ai.feature_engine.feature_builder import FeatureBuilder
from services.fusion_triage import FEATURE_NAMES

def test_model_loads_and_has_10_features():
    model = get_severity_model()
    # Force load if not loaded
    if not model.is_loaded:
        model.load_model()
    
    assert model.is_loaded
    assert model._fusion_available
    
    # Verify metadata is accessible
    health = model.health_check()
    assert health["status"] == "ready"
    assert health["model_type"] == "xgboost"
    assert health.get("metadata_loaded", False)
    
    # Verify exactly 10 features are expected in the FEATURE_NAMES list
    assert len(FEATURE_NAMES) == 10
    expected_order = [
        "image_score", "nlp_score", "sensor_score", "medical_risk",
        "has_image", "has_nlp", "has_sensor", "mean_signal", "max_signal", "signal_count"
    ]
    assert FEATURE_NAMES == expected_order

def test_inference_probability_sums_to_one():
    model = get_severity_model()
    builder = FeatureBuilder()
    
    req = TriageRequest(text="Minor headache.")
    ai_in = AIInput(request_id="test-id", symptoms=req.text)
    
    fv = builder.build(ai_in)
    pred = model.predict(fv)
    
    assert pred.class_probabilities is not None
    # Sum of probabilities should be very close to 1.0
    prob_sum = sum(pred.class_probabilities.values())
    assert abs(prob_sum - 1.0) < 0.01

def test_prediction_class_validity():
    model = get_severity_model()
    builder = FeatureBuilder()
    
    req = TriageRequest(text="Massive collision, people trapped.")
    ai_in = AIInput(request_id="test-id", symptoms=req.text)
    
    fv = builder.build(ai_in)
    pred = model.predict(fv)
    
    assert pred.severity_class.name in ["CRITICAL", "HIGH", "MODERATE", "LOW"]
    assert pred.severity_score >= 0.0 and pred.severity_score <= 1.0

def test_shap_factors_returned():
    model = get_severity_model()
    builder = FeatureBuilder()
    
    req = TriageRequest(text="Deep cut and bleeding.")
    ai_in = AIInput(request_id="test-id", symptoms=req.text)
    
    fv = builder.build(ai_in)
    pred = model.predict(fv)
    
    assert len(pred.shap_factors) > 0
    # The top SHAP feature should be one of the known 10 features
    assert pred.shap_factors[0].feature in FEATURE_NAMES
