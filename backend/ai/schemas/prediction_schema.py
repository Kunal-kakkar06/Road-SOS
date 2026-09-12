"""
ai/schemas/prediction_schema.py
================================
Output schema from the ML severity model.

This is the authoritative severity estimate produced by the model layer.
It is then passed to the decision engine which converts it into actions.

IMPORTANT — Medical Safety:
  severity_class and severity_score represent a RISK ESTIMATE only.
  They are decision-support tools, not medical diagnoses.
  All downstream consumers must present them with appropriate caveats.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SeverityClass(str, Enum):
    """Canonical severity classes aligned with existing P1–P4 system."""

    CRITICAL = "CRITICAL"   # P1 — immediate dispatch required
    HIGH = "HIGH"           # P2 — urgent, within 10 minutes
    MODERATE = "MODERATE"   # P3 — stable, within 30 minutes
    LOW = "LOW"             # P4 — minor, self-transport may be appropriate

    # Convenience converters
    @classmethod
    def from_p_code(cls, p: str) -> "SeverityClass":
        """Convert existing P1/P2/P3/P4 codes to SeverityClass."""
        mapping = {"P1": cls.CRITICAL, "P2": cls.HIGH, "P3": cls.MODERATE, "P4": cls.LOW}
        return mapping.get(p.upper(), cls.MODERATE)

    def to_p_code(self) -> str:
        """Convert back to the P-code used by existing services."""
        mapping = {
            self.CRITICAL: "P1",
            self.HIGH: "P2",
            self.MODERATE: "P3",
            self.LOW: "P4",
        }
        return mapping[self]

    def to_display_label(self) -> str:
        labels = {
            self.CRITICAL: "Critical — immediate dispatch required",
            self.HIGH: "Serious — urgent, within 10 minutes",
            self.MODERATE: "Moderate — stable, within 30 minutes",
            self.LOW: "Minor — self-transport may be appropriate",
        }
        return labels[self]

    def to_color(self) -> str:
        colors = {
            self.CRITICAL: "#ba1a1a",
            self.HIGH: "#fca311",
            self.MODERATE: "#006687",
            self.LOW: "#27AE60",
        }
        return colors[self]


class SHAPFactor(BaseModel):
    """A single SHAP explanation factor for model explainability."""

    feature: str
    impact: float
    direction: str = Field(description="'increases' or 'decreases' severity")
    label: str = Field(description="Human-readable description of this factor.")


class SeverityPrediction(BaseModel):
    """
    Structured output from the ML severity model.

    This object travels through the pipeline from the model layer →
    decision engine → orchestrator → (optionally) LLM explainer.
    """

    # Core prediction
    severity_class: SeverityClass
    severity_score: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Normalised risk estimate: 0.0 = minimal risk, 1.0 = maximum risk. "
            "This is a DECISION-SUPPORT estimate, not a medical diagnosis."
        ),
    )
    confidence: float = Field(ge=0.0, le=1.0)

    # Probability distribution across all severity classes
    class_probabilities: Optional[Dict[str, float]] = Field(
        None, description="Per-class probabilities: CRITICAL, HIGH, MODERATE, LOW."
    )

    # SHAP explainability (populated when XGBoost model is loaded)
    shap_factors: List[SHAPFactor] = Field(default_factory=list)

    # Model provenance
    model_version: str = "1.0.0"
    model_type: str = Field(
        description="e.g. 'xgboost_fusion', 'rule_based_fallback', 'mock'."
    )
    training_data_type: str = Field(
        default="synthetic",
        description="Type of data the model was trained on. e.g. 'synthetic', 'clinical'."
    )
    feature_version: str = Field(
        default="1.0",
        description="Version of the feature extraction pipeline."
    )

    # Feature summary (for transparency)
    feature_summary: Dict[str, Any] = Field(default_factory=dict)

    # Signals that contributed to this prediction
    signals_used: Dict[str, bool] = Field(
        default_factory=dict,
        description="e.g. {'image': True, 'nlp': True, 'sensor': False}",
    )

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
