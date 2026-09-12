import pytest
from unittest.mock import patch
import services.fusion_triage
from ai.models.severity_model import SeverityModel
from ai.schemas.feature_schema import FeatureVector, TextFeatures, ImageFeatures, AudioFeatures, LocationFeatures, PatientFeatures

def test_fallback_activated_on_load_failure():
    # Force the module singleton to None so it tries to load
    original_model = services.fusion_triage._model
    original_explainer = services.fusion_triage._explainer
    original_error = services.fusion_triage._model_load_error
    services.fusion_triage._model = None
    
    try:
        with patch("services.fusion_triage.joblib.load") as mock_load:
            mock_load.side_effect = Exception("Simulated disk failure")
            
            # Initialize severity model
            model = SeverityModel()
            model.load_model()
        
        # It should fall back to rule-based
        assert model._fusion_available is False
        
        # Check health endpoint
        health = model.health_check()
        assert health["status"] == "degraded"
        assert health["model_type"] == "rule_based_fallback"
        assert "Simulated disk failure" in health["detail"]
        
        # Inference should still work (using fallback)
        features = FeatureVector(
            text=TextFeatures(),
            patient=PatientFeatures(),
            audio=AudioFeatures(),
            image=ImageFeatures(image_available=True, image_severity_score=0.9),
            location=LocationFeatures(),
            sensor_available=False,
            sensor_score=None,
            signal_count=1
        )
        prediction = model.predict(features)
        
        assert prediction.model_type == "rule_based_fallback"
        assert prediction.severity_class.name in ["CRITICAL", "HIGH", "MODERATE", "LOW"]
        assert len(prediction.shap_factors) > 0
        assert "Rule-based" in prediction.shap_factors[0].label
    finally:
        # Restore global state so other tests don't fail
        services.fusion_triage._model = original_model
        services.fusion_triage._explainer = original_explainer
        services.fusion_triage._model_load_error = original_error
        # Also reset SeverityModel singleton
        import ai.models.severity_model
        ai.models.severity_model._severity_model = None
