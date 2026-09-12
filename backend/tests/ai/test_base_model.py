"""
tests/ai/test_base_model.py
Tests that BaseAIModel ABC enforces the interface contract correctly.
"""
import pytest
from ai.models.base_model import BaseAIModel
from ai.schemas.feature_schema import FeatureVector
from ai.schemas.prediction_schema import SeverityPrediction, SeverityClass


class MinimalConcreteModel(BaseAIModel):
    """Minimal valid implementation for testing the ABC."""

    def load_model(self):
        self._loaded_flag = True

    def predict(self, features: FeatureVector) -> SeverityPrediction:
        return SeverityPrediction(
            severity_class=SeverityClass.LOW,
            severity_score=0.2,
            confidence=0.9,
            model_version="test-1.0",
            model_type="mock",
            feature_summary={},
        )

    def predict_proba(self, features: FeatureVector):
        return {"LOW": 0.9, "MODERATE": 0.1, "HIGH": 0.0, "CRITICAL": 0.0}

    def get_model_version(self) -> str:
        return "test-1.0"

    def health_check(self):
        return {"status": "ok", "model_type": "mock"}

    @property
    def is_loaded(self) -> bool:
        return getattr(self, "_loaded_flag", False)


def test_cannot_instantiate_abstract_base():
    with pytest.raises(TypeError):
        BaseAIModel()


def test_concrete_model_implements_all_methods():
    model = MinimalConcreteModel()
    model.load_model()
    assert model.is_loaded is True


def test_predict_returns_severity_prediction():
    model = MinimalConcreteModel()
    fv = FeatureVector()
    pred = model.predict(fv)
    assert isinstance(pred, SeverityPrediction)
    assert pred.severity_class == SeverityClass.LOW


def test_predict_proba_returns_dict():
    model = MinimalConcreteModel()
    fv = FeatureVector()
    proba = model.predict_proba(fv)
    assert isinstance(proba, dict)
    assert sum(proba.values()) == pytest.approx(1.0, abs=0.01)


def test_health_check_returns_dict():
    model = MinimalConcreteModel()
    health = model.health_check()
    assert "status" in health
    assert "model_type" in health


def test_model_version():
    model = MinimalConcreteModel()
    assert model.get_model_version() == "test-1.0"
