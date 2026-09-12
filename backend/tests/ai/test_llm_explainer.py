"""
tests/ai/test_llm_explainer.py
Tests for LLMExplainer hierarchy — no real Claude API calls.
"""
import pytest
from unittest.mock import MagicMock, patch
from ai.llm.explainer import ClaudeExplainer, NullExplainer, get_explainer
from ai.schemas.prediction_schema import SeverityClass, SeverityPrediction
from ai.schemas.decision_schema import EmergencyDecision


def make_prediction():
    return SeverityPrediction(
        severity_class=SeverityClass.HIGH,
        severity_score=0.75,
        confidence=0.75,
        model_version="test",
        model_type="mock",
        feature_summary={},
    )


def make_decision():
    return EmergencyDecision(
        priority="URGENT",
        recommended_action="Seek urgent medical attention.",
        actions=["Call ambulance", "Stay calm"],
        hospital_required=True,
        emergency_contact_required=True,
        responder_required=False,
        estimated_eta_minutes=15,
        reasoning="HIGH severity detected.",
    )


class TestNullExplainer:
    def setup_method(self):
        self.explainer = NullExplainer()

    def test_is_not_available(self):
        assert self.explainer.is_available() is False

    def test_explain_returns_none(self):
        result = self.explainer.explain(make_prediction(), make_decision())
        assert result is None

    def test_health_check_returns_disabled(self):
        health = self.explainer.health_check()
        assert health["status"] == "disabled"

    def test_explain_never_raises(self):
        result = self.explainer.explain(None, None, None)
        assert result is None


class TestClaudeExplainer:
    def test_not_available_with_empty_key(self):
        explainer = ClaudeExplainer(api_key="")
        assert explainer.is_available() is False

    def test_not_available_with_placeholder_key(self):
        explainer = ClaudeExplainer(api_key="your_anthropic_api_key_here")
        assert explainer.is_available() is False

    def test_available_with_real_looking_key(self):
        explainer = ClaudeExplainer(api_key="sk-ant-api03-real-key")
        assert explainer.is_available() is True

    def test_explain_returns_none_when_not_available(self):
        explainer = ClaudeExplainer(api_key="")
        result = explainer.explain(make_prediction(), make_decision())
        assert result is None

    def test_explain_calls_anthropic_when_available(self):
        explainer = ClaudeExplainer(api_key="sk-ant-api03-real-key")
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Patient shows signs of high severity.")]

        # anthropic is imported at call-time inside explain(), patch at module level
        mock_anthropic_module = MagicMock()
        mock_client = MagicMock()
        mock_anthropic_module.Anthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_response

        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = explainer.explain(make_prediction(), make_decision())
        assert result == "Patient shows signs of high severity."

    def test_explain_returns_none_on_api_error(self):
        explainer = ClaudeExplainer(api_key="sk-ant-api03-real-key")
        mock_anthropic_module = MagicMock()
        mock_anthropic_module.Anthropic.side_effect = RuntimeError("API error")
        with patch.dict("sys.modules", {"anthropic": mock_anthropic_module}):
            result = explainer.explain(make_prediction(), make_decision())
        assert result is None

    def test_health_check_with_key(self):
        explainer = ClaudeExplainer(api_key="sk-ant-api03-real-key")
        health = explainer.health_check()
        assert health["status"] == "configured"
        assert health["provider"] == "claude"


class TestGetExplainer:
    def test_returns_null_when_disabled(self):
        mock_config = MagicMock()
        mock_config.enable_llm_explanation = False
        explainer = get_explainer(config=mock_config)
        assert isinstance(explainer, NullExplainer)

    def test_returns_claude_when_enabled(self):
        mock_config = MagicMock()
        mock_config.enable_llm_explanation = True
        mock_config.llm_provider = "claude"
        mock_config.anthropic_api_key = "sk-ant-api03-real-key"
        mock_config.llm_timeout_seconds = 15
        explainer = get_explainer(config=mock_config)
        assert isinstance(explainer, ClaudeExplainer)
