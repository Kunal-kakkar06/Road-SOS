"""
ai/models/base_model.py
========================
Abstract base class for all AI models in the RoadSOS pipeline.

Any future model (Logistic Regression, Random Forest, XGBoost,
a new neural network) must implement this interface.  This ensures
the orchestrator and decision engine can swap models without changing
any calling code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ai.schemas.feature_schema import FeatureVector
from ai.schemas.prediction_schema import SeverityPrediction


class BaseAIModel(ABC):
    """
    Abstract interface that all RoadSOS ML models must implement.

    Design contract:
    - load_model()  is called once at startup (lazy or eager)
    - predict()     returns a SeverityPrediction (never raises — uses fallback)
    - health_check() returns a safe dict for the /api/ai/health endpoint
    - No model may silently invent values for missing features
    - No model may call external APIs (Claude, HTTP) directly
    """

    @abstractmethod
    def load_model(self) -> None:
        """
        Load model weights / artefacts from disk.

        Called once during application startup or on first inference.
        Must not raise if the model file is missing — set an internal
        flag and use the rule-based fallback instead.
        """

    @abstractmethod
    def predict(self, features: FeatureVector) -> SeverityPrediction:
        """
        Run inference on the provided feature vector.

        Must NEVER raise an unhandled exception.  If the model is
        unavailable, return a SeverityPrediction based on the rule-based
        fallback with model_type='rule_based_fallback'.

        Args:
            features: Complete FeatureVector from the FeatureBuilder.

        Returns:
            SeverityPrediction with all required fields populated.
        """

    @abstractmethod
    def predict_proba(self, features: FeatureVector) -> Dict[str, float]:
        """
        Return per-class probability estimates.

        Returns:
            Dict mapping SeverityClass names to float probabilities.
            e.g. {"CRITICAL": 0.7, "HIGH": 0.2, "MODERATE": 0.08, "LOW": 0.02}
        """

    @abstractmethod
    def get_model_version(self) -> str:
        """Return a string identifying the model version (e.g. '1.0.0')."""

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Return a safe health summary for the /api/ai/health endpoint.

        Must never include secrets or raw exception messages.

        Returns:
            Dict with at minimum: {"status": "ok"|"degraded"|"unavailable", "model_type": str}
        """

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """True if the model artefacts were successfully loaded from disk."""
