"""
tests/ai/test_severity_model.py
Tests for SeverityModel — mocks fusion_triage to avoid .pkl dependency.
The functions are imported locally inside methods, so we patch at the
services.fusion_triage module level.
"""
import pytest
from unittest.mock import patch, MagicMock
from ai.models.severity_model import SeverityModel
from ai.schemas.feature_schema import FeatureVector, AudioFeatures, ImageFeatures, TextFeatures
from ai.schemas.prediction_schema import SeverityClass


_MOCK_P1_RESULT = {
    "severity": "P1",
    "severity_label": "Critical — immediate dispatch required",
    "severity_color": "#ba1a1a",
    "confidence": 0.92,
    "probabilities": {"P1": 0.92, "P2": 0.05, "P3": 0.02, "P4": 0.01},
    "shap_factors": [
        {"feature": "nlp_score", "impact": 0.45, "direction": "increases", "label": "Voice symptom score"},
    ],
    "signals_used": {"image": False, "nlp": True, "sensor": False},
}

_MOCK_RULE_RESULT = {
    "severity": "P3",
    "severity_label": "Moderate — stable, within 30 minutes",
    "severity_color": "#006687",
    "confidence": 0.55,
    "probabilities": {},
    "shap_factors": [{"label": "Rule-based estimate — XGBoost model not loaded"}],
    "signals_used": {"image": False, "nlp": True, "sensor": False},
}


def make_feature_vector_with_nlp(score=0.8) -> FeatureVector:
    return FeatureVector(
        text=TextFeatures(raw_text_available=True, nlp_severity_score=score),
        audio=AudioFeatures(audio_available=True, nlp_severity_score=score),
        signal_count=2,
    )


def test_severity_model_load_model_with_fusion_available():
    model = SeverityModel()
    with patch("services.fusion_triage.get_model", return_value=(MagicMock(), MagicMock())):
        model.load_model()
    assert model.is_loaded is True


def test_severity_model_load_model_without_pkl():
    model = SeverityModel()
    with patch("services.fusion_triage.get_model", return_value=(None, None)):
        model.load_model()
    assert model.is_loaded is True
    assert model._fusion_available is False


def test_predict_returns_critical_for_p1():
    model = SeverityModel()
    fv = make_feature_vector_with_nlp(0.9)
    with patch("services.fusion_triage.fuse_triage_signals", return_value=_MOCK_P1_RESULT):
        pred = model.predict(fv)
    assert pred.severity_class == SeverityClass.CRITICAL
    assert pred.confidence == pytest.approx(0.92)
    assert pred.model_type == "xgboost"
    assert len(pred.shap_factors) == 1


def test_predict_returns_moderate_for_rule_based():
    model = SeverityModel()
    fv = make_feature_vector_with_nlp(0.5)
    with patch("services.fusion_triage.fuse_triage_signals", return_value=_MOCK_RULE_RESULT):
        pred = model.predict(fv)
    assert pred.severity_class == SeverityClass.MODERATE
    assert pred.model_type == "rule_based_fallback"


def test_predict_never_raises_on_fusion_crash():
    model = SeverityModel()
    fv = FeatureVector()
    with patch("services.fusion_triage.fuse_triage_signals",
               side_effect=RuntimeError("fusion crashed")):
        pred = model.predict(fv)
    assert pred.severity_class == SeverityClass.MODERATE
    assert pred.model_type == "emergency_fallback"


def test_predict_proba_sums_to_one():
    model = SeverityModel()
    fv = make_feature_vector_with_nlp(0.8)
    with patch("services.fusion_triage.fuse_triage_signals", return_value=_MOCK_P1_RESULT):
        proba = model.predict_proba(fv)
    total = sum(proba.values())
    assert total == pytest.approx(1.0, abs=0.05)


def test_health_check_structure():
    model = SeverityModel()
    health = model.health_check()
    assert "status" in health
    assert "model_type" in health
    assert "model_version" in health


def test_severity_class_p_code_conversion():
    assert SeverityClass.from_p_code("P1") == SeverityClass.CRITICAL
    assert SeverityClass.from_p_code("P2") == SeverityClass.HIGH
    assert SeverityClass.from_p_code("P3") == SeverityClass.MODERATE
    assert SeverityClass.from_p_code("P4") == SeverityClass.LOW
    assert SeverityClass.CRITICAL.to_p_code() == "P1"
