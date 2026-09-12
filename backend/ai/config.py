"""
ai/config.py
============
Central configuration for the AI subsystem.

All values are read from environment variables so the same codebase works
in local dev (SQLite, no cloud keys) and Railway production (PostgreSQL,
real API keys).

Never hard-code secrets here.  Add new variables to .env.example only
with placeholder values so the file stays gitignored-safe.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AIConfig:
    # ── Model identity ─────────────────────────────────────────
    severity_model_version: str = field(
        default_factory=lambda: os.getenv("AI_SEVERITY_MODEL_VERSION", "1.0.0")
    )

    # ── LLM explanation (optional) ────────────────────────────
    enable_llm_explanation: bool = field(
        default_factory=lambda: os.getenv(
            "AI_ENABLE_LLM_EXPLANATION", "false"
        ).lower() == "true"
    )
    llm_provider: str = field(
        default_factory=lambda: os.getenv("AI_LLM_PROVIDER", "claude").lower()
    )
    # Anthropic key – already used by existing triage route
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )

    # ── RAG (not yet configured) ──────────────────────────────
    enable_rag: bool = field(
        default_factory=lambda: os.getenv("AI_ENABLE_RAG", "false").lower() == "true"
    )

    # ── Optional ML sub-features ─────────────────────────────
    enable_clinical_bert: bool = field(
        default_factory=lambda: os.getenv(
            "ENABLE_CLINICAL_BERT", "false"
        ).lower() == "true"
    )

    # ── Operational limits ────────────────────────────────────
    llm_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("AI_LLM_TIMEOUT_SECONDS", "15"))
    )
    max_rag_results: int = field(
        default_factory=lambda: int(os.getenv("AI_MAX_RAG_RESULTS", "3"))
    )

    def is_llm_available(self) -> bool:
        """Return True only when LLM explanation is both enabled and keyed."""
        return (
            self.enable_llm_explanation
            and bool(self.anthropic_api_key)
            and self.anthropic_api_key not in ("", "your_anthropic_api_key_here")
        )

    def is_rag_available(self) -> bool:
        """Return True only when RAG is enabled and configured."""
        return self.enable_rag

    def as_dict(self) -> dict:
        """Safe representation for health-check responses (no secrets)."""
        return {
            "severity_model_version": self.severity_model_version,
            "enable_llm_explanation": self.enable_llm_explanation,
            "llm_provider": self.llm_provider,
            "llm_available": self.is_llm_available(),
            "enable_rag": self.enable_rag,
            "rag_available": self.is_rag_available(),
            "enable_clinical_bert": self.enable_clinical_bert,
        }


# Module-level singleton — import this everywhere
ai_config = AIConfig()
