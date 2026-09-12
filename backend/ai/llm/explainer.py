"""
ai/llm/explainer.py
====================
Optional LLM explanation interface.

Architecture design:
  ML model + decision engine produce the CORE recommendation — deterministic.
  LLMExplainer is an OPTIONAL downstream step that converts the structured
  output into a natural-language explanation for the end user.

The LLM must never:
  - override the severity class
  - override the recommended_action
  - make medical diagnoses
  - be a required step (pipeline must succeed if LLM is unavailable)

Provider switching:
  Change AI_LLM_PROVIDER env var to use a different provider.
  Currently: claude (existing integration)
  Future:    gemini | openai | local
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from ai.schemas.prediction_schema import SeverityPrediction
from ai.schemas.decision_schema import EmergencyDecision

logger = logging.getLogger("roadsos.ai.llm")


# ── Abstract interface ─────────────────────────────────────────────

class LLMExplainer(ABC):
    """
    Abstract interface for optional LLM-generated explanations.

    Any provider (Claude, Gemini, OpenAI, local) must implement explain().
    The orchestrator calls explain() only when is_available() returns True.
    """

    @abstractmethod
    def explain(
        self,
        prediction: SeverityPrediction,
        decision: EmergencyDecision,
        retrieved_context: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Generate a natural-language explanation for the given prediction + decision.

        Args:
            prediction:         Severity prediction from the ML model.
            decision:           Emergency decision from the decision engine.
            retrieved_context:  Optional list of text chunks from RAG retrieval.

        Returns:
            A natural-language explanation string, or None if unavailable.
            Must NEVER raise an unhandled exception.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this explainer is configured and ready."""

    @abstractmethod
    def health_check(self) -> dict:
        """Return a safe health summary for /api/ai/health."""


# ── Null explainer (safe default when LLM is disabled) ────────────

class NullExplainer(LLMExplainer):
    """
    No-op explainer used when LLM explanation is disabled or unconfigured.

    Always returns None so the pipeline degrades gracefully.
    """

    def explain(self, prediction, decision, retrieved_context=None) -> None:
        return None

    def is_available(self) -> bool:
        return False

    def health_check(self) -> dict:
        return {
            "status": "disabled",
            "detail": "LLM explanation disabled. Set AI_ENABLE_LLM_EXPLANATION=true to activate.",
        }


# ── Claude implementation ──────────────────────────────────────────

class ClaudeExplainer(LLMExplainer):
    """
    LLM explainer backed by the existing Anthropic Claude integration.

    This wraps the same Claude client already used by the existing
    /api/triage endpoint.  It does NOT introduce any new dependencies.

    The explanation prompt is carefully framed to:
    - Present only the pre-computed severity as context
    - Ask Claude to explain it in plain language
    - NOT ask Claude to re-diagnose or override the decision
    """

    def __init__(self, api_key: str, timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._is_keyed = bool(api_key) and api_key not in (
            "", "your_anthropic_api_key_here"
        )

    def explain(
        self,
        prediction: SeverityPrediction,
        decision: EmergencyDecision,
        retrieved_context: Optional[List[str]] = None,
    ) -> Optional[str]:
        if not self._is_keyed:
            return None

        try:
            import anthropic

            context_block = ""
            if retrieved_context:
                context_block = "\n\nRelevant medical context:\n" + "\n---\n".join(
                    retrieved_context[:3]
                )

            severity_label = prediction.severity_class.to_display_label()
            shap_summary = ", ".join(
                f"{f.feature} ({f.direction} severity)"
                for f in prediction.shap_factors[:3]
            ) if prediction.shap_factors else "multiple factors"

            prompt = f"""You are a calm, professional emergency medical assistant.

A patient's condition has been assessed by our AI triage system with the following result:

Severity: {severity_label} (confidence: {prediction.confidence:.0%})
Key contributing factors: {shap_summary}
Recommended action: {decision.recommended_action}
{context_block}

Write a brief (2-3 sentence), clear, compassionate explanation of this assessment for the patient or bystander.
Do NOT present this as a medical diagnosis.
Use plain language. Do NOT suggest the severity is different from what was assessed.
Do not include any JSON, markdown headers, or lists — plain prose only."""

            client = anthropic.Anthropic(api_key=self._api_key)
            message = client.messages.create(
                model="claude-3-haiku-20240307",  # fastest/cheapest for explanation
                max_tokens=200,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()

        except Exception as exc:
            logger.warning("[ClaudeExplainer] Explanation failed: %s", exc)
            return None

    def is_available(self) -> bool:
        return self._is_keyed

    def health_check(self) -> dict:
        return {
            "status": "configured" if self._is_keyed else "key_missing",
            "provider": "claude",
            "detail": (
                "Claude API key is set."
                if self._is_keyed
                else "ANTHROPIC_API_KEY is missing or placeholder — explanation disabled."
            ),
        }


# ── Factory ────────────────────────────────────────────────────────

def get_explainer(config=None) -> LLMExplainer:
    """
    Return the appropriate LLMExplainer based on configuration.

    Uses the module-level ai_config singleton by default.
    Pass a custom config object in tests.
    """
    from ai.config import ai_config as _default_config
    cfg = config or _default_config

    if not cfg.enable_llm_explanation:
        return NullExplainer()

    provider = cfg.llm_provider.lower()

    if provider == "claude":
        return ClaudeExplainer(
            api_key=cfg.anthropic_api_key,
            timeout_seconds=cfg.llm_timeout_seconds,
        )

    # Future providers
    # elif provider == "gemini":
    #     return GeminiExplainer(...)
    # elif provider == "openai":
    #     return OpenAIExplainer(...)

    logger.warning(
        "[LLM] Unknown provider '%s' — falling back to NullExplainer.", provider
    )
    return NullExplainer()
