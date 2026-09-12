"""
ai/pipeline/orchestrator.py
============================
Central AI orchestration service for RoadSOS.

AIOrchestrator.process() is the single entry point for AI inference.
It coordinates all components in the correct order and handles failures
at each stage independently — a failure in RAG or LLM does NOT abort
the core prediction + decision flow.

Flow:
  1. Validate input
  2. Build feature vector (feature_engine)
  3. Run severity model (ml model)
  4. Run decision engine (deterministic rules)
  5. Rank hospitals (optional — only when location + hospitals provided)
  6. Retrieve RAG context (optional — only when RAG is configured)
  7. Generate LLM explanation (optional — only when LLM is configured)
  8. Return UnifiedAIResponse

The orchestrator does NOT contain any ML logic, domain rules, or prompt
engineering.  Those belong in their respective modules.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from ai.config import AIConfig, ai_config as _default_config
from ai.feature_engine.feature_builder import FeatureBuilder
from ai.models.severity_model import SeverityModel, get_severity_model
from ai.decision.emergency_decision import EmergencyDecisionEngine
from ai.decision.hospital_ranker import HospitalRanker
from ai.rag.retriever import RAGRetriever
from ai.llm.explainer import LLMExplainer, get_explainer
from ai.schemas.input_schema import AIInput
from ai.schemas.decision_schema import (
    EmergencyDecision,
    HospitalRecommendation,
    ProcessingMetadata,
    RAGSource,
    UnifiedAIResponse,
)
from ai.schemas.prediction_schema import SeverityPrediction

logger = logging.getLogger("roadsos.ai.pipeline")


class AIOrchestrator:
    """
    Coordinates all AI pipeline components.

    Designed for dependency injection — all components are passed at
    construction time so tests can mock any component independently.

    Usage (production):
        orchestrator = AIOrchestrator()
        response = orchestrator.process(ai_input)

    Usage (test):
        orchestrator = AIOrchestrator(model=MockModel(), explainer=NullExplainer())
        response = orchestrator.process(ai_input)
    """

    def __init__(
        self,
        config: Optional[AIConfig] = None,
        feature_builder: Optional[FeatureBuilder] = None,
        model: Optional[SeverityModel] = None,
        decision_engine: Optional[EmergencyDecisionEngine] = None,
        hospital_ranker: Optional[HospitalRanker] = None,
        rag_retriever: Optional[RAGRetriever] = None,
        llm_explainer: Optional[LLMExplainer] = None,
    ):
        self._config = config or _default_config
        self._feature_builder = feature_builder or FeatureBuilder()
        self._model = model or get_severity_model()
        self._decision_engine = decision_engine or EmergencyDecisionEngine()
        self._hospital_ranker = hospital_ranker or HospitalRanker()
        self._rag_retriever = rag_retriever or RAGRetriever(config=self._config)
        self._llm_explainer = llm_explainer or get_explainer(config=self._config)

    def process(
        self,
        ai_input: AIInput,
        hospitals: Optional[List[Dict[str, Any]]] = None,
    ) -> UnifiedAIResponse:
        """
        Run the full AI pipeline for a single inference request.

        Args:
            ai_input:   Validated AIInput from the calling router.
            hospitals:  Optional list of hospital dicts for ranking.
                        Pass None to skip hospital ranking.

        Returns:
            UnifiedAIResponse with all available fields populated.
        """
        start_time = time.monotonic()
        stages_completed: List[str] = []
        stages_failed: List[str] = []
        non_fatal_errors: List[str] = []

        logger.info(
            "[Orchestrator] Starting pipeline for request_id=%s", ai_input.request_id
        )

        # ── Stage 1: Feature Extraction ───────────────────────
        try:
            features = self._feature_builder.build(ai_input)
            stages_completed.append("feature_extraction")
            logger.debug("[Orchestrator] Features: %s", features.summary_dict())
        except Exception as exc:
            logger.error("[Orchestrator] feature_extraction failed: %s", exc)
            stages_failed.append("feature_extraction")
            # Cannot continue without features
            raise RuntimeError(f"Feature extraction failed: {exc}") from exc

        # ── Stage 2: ML Inference ─────────────────────────────
        try:
            prediction: SeverityPrediction = self._model.predict(features)
            stages_completed.append("ml_inference")
            logger.info(
                "[Orchestrator] Prediction: class=%s confidence=%.2f model=%s",
                prediction.severity_class,
                prediction.confidence,
                prediction.model_type,
            )
        except Exception as exc:
            logger.error("[Orchestrator] ml_inference failed: %s", exc)
            stages_failed.append("ml_inference")
            raise RuntimeError(f"ML inference failed: {exc}") from exc

        # ── Stage 3: Decision Engine ──────────────────────────
        try:
            decision: EmergencyDecision = self._decision_engine.make_decision(prediction)
            stages_completed.append("decision_engine")
        except Exception as exc:
            logger.error("[Orchestrator] decision_engine failed: %s", exc)
            stages_failed.append("decision_engine")
            # Decision engine has its own fallback — should not reach here
            decision = self._decision_engine._fallback_decision()
            non_fatal_errors.append(f"decision_engine: {exc}")

        # ── Stage 4: Hospital Ranking (optional) ──────────────
        hospital_recommendations: List[HospitalRecommendation] = []
        if hospitals is not None:
            try:
                hospital_recommendations = self._hospital_ranker.rank(
                    user_lat=ai_input.latitude,
                    user_lng=ai_input.longitude,
                    hospitals=hospitals,
                    prediction=prediction,
                )
                stages_completed.append("hospital_ranking")
            except Exception as exc:
                logger.error("[Orchestrator] hospital_ranking failed: %s", exc)
                stages_failed.append("hospital_ranking")
                non_fatal_errors.append(f"hospital_ranking: {exc}")

        # ── Stage 5: RAG Retrieval (optional) ─────────────────
        rag_sources: List[RAGSource] = []
        rag_used = False
        if self._config.is_rag_available():
            try:
                rag_query = ai_input.symptoms or prediction.severity_class.to_display_label()
                rag_result = self._rag_retriever.retrieve(
                    query=rag_query, top_k=self._config.max_rag_results
                )
                if rag_result.is_available():
                    rag_sources = [
                        RAGSource(
                            source_id=doc.source_id,
                            title=doc.title,
                            content=doc.content,
                            relevance_score=doc.relevance_score,
                            source_type=doc.source_type,
                        )
                        for doc in rag_result.documents
                    ]
                    rag_used = True
                stages_completed.append("rag_retrieval")
            except Exception as exc:
                logger.warning("[Orchestrator] rag_retrieval failed (non-fatal): %s", exc)
                stages_failed.append("rag_retrieval")
                non_fatal_errors.append(f"rag_retrieval: {exc}")

        # ── Stage 6: LLM Explanation (optional) ───────────────
        explanation: Optional[str] = None
        llm_used = False
        if self._llm_explainer.is_available():
            try:
                retrieved_text = [s.content for s in rag_sources] if rag_sources else None
                explanation = self._llm_explainer.explain(
                    prediction=prediction,
                    decision=decision,
                    retrieved_context=retrieved_text,
                )
                llm_used = explanation is not None
                stages_completed.append("llm_explanation")
            except Exception as exc:
                logger.warning("[Orchestrator] llm_explanation failed (non-fatal): %s", exc)
                stages_failed.append("llm_explanation")
                non_fatal_errors.append(f"llm_explanation: {exc}")

        # ── Assemble response ──────────────────────────────────
        elapsed_ms = round((time.monotonic() - start_time) * 1000, 1)
        logger.info(
            "[Orchestrator] Completed request_id=%s in %sms — stages=%s",
            ai_input.request_id,
            elapsed_ms,
            stages_completed,
        )

        return UnifiedAIResponse(
            request_id=ai_input.request_id,
            prediction=prediction,
            decision=decision,
            hospital_recommendations=hospital_recommendations,
            retrieved_sources=rag_sources,
            explanation=explanation,
            model_metadata={
                "model_version": self._model.get_model_version(),
                "model_type": prediction.model_type,
            },
            processing_metadata=ProcessingMetadata(
                stages_completed=stages_completed,
                stages_failed=stages_failed,
                processing_time_ms=elapsed_ms,
                model_fallback_used=prediction.model_type == "rule_based_fallback",
                rag_used=rag_used,
                llm_used=llm_used,
                errors=non_fatal_errors,
            ),
        )

    def health_check(self) -> Dict[str, Any]:
        """Aggregate health from all components. Safe for /api/ai/health."""
        return {
            "orchestrator": "ok",
            "model": self._model.health_check(),
            "rag": self._rag_retriever.health_check(),
            "llm": self._llm_explainer.health_check(),
            "config": self._config.as_dict(),
        }


# ── Module-level singleton ─────────────────────────────────────────

_orchestrator: Optional[AIOrchestrator] = None


def get_orchestrator() -> AIOrchestrator:
    """Return the module-level AIOrchestrator singleton."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator
