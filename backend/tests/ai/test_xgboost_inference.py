import pytest
from ai.models.severity_model import get_severity_model
from ai.schemas.feature_schema import FeatureVector, PatientFeatures, TextFeatures, ImageFeatures, AudioFeatures, LocationFeatures
from ai.schemas.prediction_schema import SeverityClass

@pytest.fixture(autouse=True)
def setup_model():
    import ai.models.severity_model
    ai.models.severity_model._severity_model = None
    model = get_severity_model()
    assert model.is_loaded
    assert model._fusion_available is True
    yield model

def create_mock_features(img_score=None, nlp_score=None, sen_score=None, med_risk=0.5):
    return FeatureVector(
        text=TextFeatures(raw_text_available=bool(nlp_score), nlp_severity_score=nlp_score),
        patient=PatientFeatures(medical_risk_score=med_risk),
        audio=AudioFeatures(),
        image=ImageFeatures(image_available=bool(img_score), image_severity_score=img_score),
        location=LocationFeatures(),
        sensor_available=bool(sen_score),
        sensor_score=sen_score,
        signal_count=sum([bool(img_score), bool(nlp_score), bool(sen_score)])
    )

def test_inference_low_risk(setup_model):
    # Base signals around 0.1 -> Low risk
    features = create_mock_features(img_score=0.1, nlp_score=0.1, sen_score=0.1)
    prediction = setup_model.predict(features)
    assert prediction.severity_class == SeverityClass.LOW
    assert prediction.severity_score > 0

def test_inference_moderate_risk(setup_model):
    # Base signals around 0.55 -> Moderate risk
    features = create_mock_features(img_score=0.55, nlp_score=0.55, sen_score=0.55)
    prediction = setup_model.predict(features)
    assert prediction.severity_class == SeverityClass.MODERATE

def test_inference_high_risk(setup_model):
    # Base signals around 0.7 -> High risk
    features = create_mock_features(img_score=0.7, nlp_score=0.7, sen_score=0.7)
    prediction = setup_model.predict(features)
    assert prediction.severity_class == SeverityClass.HIGH

def test_inference_critical_risk(setup_model):
    # Base signals around 0.95 -> Critical risk
    features = create_mock_features(img_score=0.95, nlp_score=0.95, sen_score=0.95)
    prediction = setup_model.predict(features)
    assert prediction.severity_class == SeverityClass.CRITICAL

def test_probability_validation(setup_model):
    features = create_mock_features(img_score=0.9, nlp_score=0.9, sen_score=0.9)
    prediction = setup_model.predict(features)
    
    assert prediction.class_probabilities is not None
    # Check probabilities are between 0 and 1
    for cls_name, prob in prediction.class_probabilities.items():
        assert 0.0 <= prob <= 1.0
        
    # Sum should be very close to 1
    total_prob = sum(prediction.class_probabilities.values())
    assert abs(total_prob - 1.0) < 0.01
    
    # Argmax matches predicted class
    max_cls = max(prediction.class_probabilities.items(), key=lambda x: x[1])[0]
    assert max_cls == prediction.severity_class.name

def test_shap_validation(setup_model):
    features = create_mock_features(img_score=0.95, nlp_score=0.2, sen_score=None, med_risk=0.8)
    prediction = setup_model.predict(features)
    
    # SHAP factors should be returned (top 3)
    assert len(prediction.shap_factors) <= 3
    assert len(prediction.shap_factors) > 0
    
    # Check structure
    for factor in prediction.shap_factors:
        assert hasattr(factor, "feature")
        assert hasattr(factor, "impact")
        assert hasattr(factor, "direction")
        assert hasattr(factor, "label")
        assert factor.direction in ["increases", "decreases"]
