import pytest
from ai.models.severity_model import get_severity_model
from ai.schemas.feature_schema import FeatureVector, PatientFeatures, TextFeatures, ImageFeatures, AudioFeatures, LocationFeatures
from services.fusion_triage import FEATURE_NAMES

def test_feature_order_and_count():
    # The XGBoost model was trained with exactly these 10 features in this order:
    expected_features = [
        "image_score", "nlp_score", "sensor_score", "medical_risk",
        "has_image", "has_nlp", "has_sensor",
        "mean_signal", "max_signal", "signal_count"
    ]
    assert FEATURE_NAMES == expected_features, "Feature order mismatch between training and inference!"

def test_inference_uses_xgboost_when_available():
    import ai.models.severity_model
    ai.models.severity_model._severity_model = None
    model = get_severity_model()
    # It should have loaded successfully now that shap is installed
    assert model.is_loaded
    assert model._fusion_available is True

def test_model_metadata_includes_versioning():
    import ai.models.severity_model
    ai.models.severity_model._severity_model = None
    model = get_severity_model()
    health = model.health_check()
    assert health["status"] == "ready"
    assert health["model_type"] == "xgboost"
    assert "model_version" in health
    assert health["training_data_type"] == "synthetic"
    assert health["feature_version"] == "1.0"

def test_model_predict_outputs_correct_metadata():
    import ai.models.severity_model
    ai.models.severity_model._severity_model = None
    model = get_severity_model()
    features = FeatureVector(
        text=TextFeatures(),
        patient=PatientFeatures(),
        audio=AudioFeatures(),
        image=ImageFeatures(),
        location=LocationFeatures(),
        sensor_available=False,
        sensor_score=None,
        signal_count=0
    )
    prediction = model.predict(features)
    assert prediction.model_type == "xgboost"
    assert prediction.training_data_type == "synthetic"
    assert prediction.feature_version == "1.0"
