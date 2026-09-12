"""
tests/ai/test_orchestrator.py
End-to-end orchestrator tests with all components mocked.
No real Claude calls, no DB access, no file I/O.
"""
import pytest
from unittest.mock import MagicMock, patch
from ai.pipeline.orchestrator import AIOrchestrator
from ai.schemas.input_schema import AIInput
from ai.schemas.feature_schema import FeatureVector
from ai.schemas.prediction_schema import SeverityClass, SeverityPrediction
from ai.schemas.decision_schema import EmergencyDecision, UnifiedAIResponse
from ai.llm.explainer import NullExplainer
from ai.rag.retriever import RAGRetriever, RAGResult


# ── Shared fixtures / helpers ─────────────────────────────────────

def make_prediction(severity=SeverityClass.HIGH) -> SeverityPrediction:
    return SeverityPrediction(
        severity_class=severity, severity_score=0.75, confidence=0.75,
        model_version="test", model_type="mock", feature_summary={},
        signals_used={"image": False, "nlp": True, "sensor": False},
    )


def make_decision() -> EmergencyDecision:
    return EmergencyDecision(
        priority="URGENT",
        recommended_action="Seek urgent medical attention.",
        actions=["Call ambulance"],
        hospital_required=True,
        emergency_contact_required=True,
        responder_required=False,
        estimated_eta_minutes=15,
        reasoning="HIGH severity.",
    )


def make_mock_model(prediction: SeverityPrediction) -> MagicMock:
    model = MagicMock()
    model.predict.return_value = prediction
    model.predict_proba.return_value = {"HIGH": 0.75, "CRITICAL": 0.1, "MODERATE": 0.1, "LOW": 0.05}
    model.get_model_version.return_value = "test-1.0"
    model.health_check.return_value = {"status": "ok", "model_type": "mock"}
    return model


def make_mock_decision_engine(decision: EmergencyDecision) -> MagicMock:
    engine = MagicMock()
    engine.make_decision.return_value = decision
    engine._fallback_decision.return_value = decision
    return engine


def make_rag_not_configured() -> RAGRetriever:
    retriever = MagicMock(spec=RAGRetriever)
    retriever.retrieve.return_value = RAGResult(status="not_configured", documents=[])
    retriever.health_check.return_value = {"status": "not_configured"}
    return retriever


def make_mock_config(enable_llm=False, enable_rag=False) -> MagicMock:
    cfg = MagicMock()
    cfg.enable_llm_explanation = enable_llm
    cfg.enable_rag = enable_rag
    cfg.is_llm_available.return_value = False
    cfg.is_rag_available.return_value = enable_rag
    cfg.max_rag_results = 3
    cfg.as_dict.return_value = {}
    return cfg


# ── Tests ─────────────────────────────────────────────────────────

class TestAIOrchestrator:

    def _make_orchestrator(self, severity=SeverityClass.HIGH):
        pred = make_prediction(severity)
        dec = make_decision()
        mock_fb = MagicMock()
        mock_fb.build.return_value = FeatureVector()
        return AIOrchestrator(
            config=make_mock_config(),
            feature_builder=mock_fb,
            model=make_mock_model(pred),
            decision_engine=make_mock_decision_engine(dec),
            hospital_ranker=MagicMock(return_value=[]),
            rag_retriever=make_rag_not_configured(),
            llm_explainer=NullExplainer(),
        ), pred, dec

    def test_process_returns_unified_response(self):
        orch, pred, dec = self._make_orchestrator()
        ai_input = AIInput(symptoms="chest pain")
        result = orch.process(ai_input)
        assert isinstance(result, UnifiedAIResponse)

    def test_process_contains_prediction(self):
        orch, pred, dec = self._make_orchestrator()
        result = orch.process(AIInput(symptoms="chest pain"))
        assert result.prediction.severity_class == SeverityClass.HIGH

    def test_process_contains_decision(self):
        orch, pred, dec = self._make_orchestrator()
        result = orch.process(AIInput(symptoms="chest pain"))
        assert result.decision.priority == "URGENT"

    def test_process_request_id_echoed(self):
        orch, _, _ = self._make_orchestrator()
        ai_input = AIInput(request_id="my-test-id", symptoms="pain")
        result = orch.process(ai_input)
        assert result.request_id == "my-test-id"

    def test_process_no_llm_explanation_by_default(self):
        orch, _, _ = self._make_orchestrator()
        result = orch.process(AIInput(symptoms="pain"))
        assert result.explanation is None

    def test_process_rag_not_configured_returns_empty_sources(self):
        orch, _, _ = self._make_orchestrator()
        result = orch.process(AIInput(symptoms="pain"))
        assert result.retrieved_sources == []

    def test_process_metadata_has_stages(self):
        orch, _, _ = self._make_orchestrator()
        result = orch.process(AIInput(symptoms="pain"))
        assert "feature_extraction" in result.processing_metadata.stages_completed
        assert "ml_inference" in result.processing_metadata.stages_completed
        assert "decision_engine" in result.processing_metadata.stages_completed

    def test_process_metadata_has_timing(self):
        orch, _, _ = self._make_orchestrator()
        result = orch.process(AIInput(symptoms="pain"))
        assert result.processing_metadata.processing_time_ms is not None
        assert result.processing_metadata.processing_time_ms >= 0  # can be 0.0 on fast machines

    def test_hospital_ranking_skipped_when_none_passed(self):
        orch, _, _ = self._make_orchestrator()
        result = orch.process(AIInput(symptoms="pain"), hospitals=None)
        assert result.hospital_recommendations == []

    def test_hospital_ranking_called_when_hospitals_provided(self):
        pred = make_prediction()
        dec = make_decision()
        mock_fb = MagicMock()
        mock_fb.build.return_value = FeatureVector()
        mock_ranker = MagicMock()
        mock_ranker.rank.return_value = []
        orch = AIOrchestrator(
            config=make_mock_config(),
            feature_builder=mock_fb,
            model=make_mock_model(pred),
            decision_engine=make_mock_decision_engine(dec),
            hospital_ranker=mock_ranker,
            rag_retriever=make_rag_not_configured(),
            llm_explainer=NullExplainer(),
        )
        orch.process(AIInput(symptoms="pain"), hospitals=[{"name": "Test Hospital"}])
        mock_ranker.rank.assert_called_once()

    def test_feature_extraction_failure_raises(self):
        pred = make_prediction()
        dec = make_decision()
        mock_fb = MagicMock()
        mock_fb.build.side_effect = RuntimeError("extraction failed")
        orch = AIOrchestrator(
            config=make_mock_config(),
            feature_builder=mock_fb,
            model=make_mock_model(pred),
            decision_engine=make_mock_decision_engine(dec),
            hospital_ranker=MagicMock(return_value=[]),
            rag_retriever=make_rag_not_configured(),
            llm_explainer=NullExplainer(),
        )
        with pytest.raises(RuntimeError, match="Feature extraction failed"):
            orch.process(AIInput(symptoms="pain"))

    def test_health_check_returns_all_components(self):
        orch, _, _ = self._make_orchestrator()
        health = orch.health_check()
        assert "orchestrator" in health
        assert "model" in health
        assert "rag" in health
        assert "llm" in health
        assert "config" in health

    def test_critical_severity_propagated(self):
        orch, _, _ = self._make_orchestrator(severity=SeverityClass.CRITICAL)
        result = orch.process(AIInput(symptoms="cardiac arrest"))
        assert result.prediction.severity_class == SeverityClass.CRITICAL
