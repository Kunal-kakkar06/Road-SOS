"""
ai/models/severity_model.py
============================
Concrete severity model that implements BaseAIModel by wrapping
the existing services.fusion_triage module.

The fusion_triage service already contains:
  - XGBoost multi-signal fusion (loaded from models/fusion_triage.pkl)
  - SHAP TreeExplainer for explainability
  - Rule-based fallback when the .pkl is missing

This class adds NO new ML logic.  It translates between the new typed
schemas (FeatureVector → SeverityPrediction) and the existing service's
untyped dict API, so the orchestrator can treat it as a BaseAIModel.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ai.models.base_model import BaseAIModel
from ai.schemas.feature_schema import FeatureVector
from ai.schemas.prediction_schema import SeverityClass, SeverityPrediction, SHAPFactor
import json
import os

logger = logging.getLogger("roadsos.ai.models.severity")


class SeverityModel(BaseAIModel):
    """
    Wraps services.fusion_triage.fuse_triage_signals() as a BaseAIModel.

    The underlying XGBoost model is lazy-loaded by fusion_triage on first call.
    If the .pkl file is absent, fusion_triage uses its own deterministic
    rule-based fallback transparently.
    """

    def __init__(self, model_version: str = "1.0.0"):
        self._model_version = model_version
        self._loaded = False
        self._fusion_available = False
        self._metadata: Dict[str, Any] = {}

    def _load_metadata(self) -> None:
        """Attempt to load the model metadata.json if it exists."""
        from pathlib import Path
        meta_path = Path(__file__).parent.parent.parent / "models" / "metadata.json"
        if not meta_path.exists():
            meta_path = Path("models") / "metadata.json"
        try:
            if meta_path.exists():
                with open(meta_path, "r") as f:
                    self._metadata = json.load(f)
                    # Override the hardcoded version if metadata has it
                    if "model_version" in self._metadata:
                        self._model_version = self._metadata["model_version"]
        except Exception as exc:
            logger.warning("[SeverityModel] Could not load metadata.json: %s", exc)

    # ── BaseAIModel interface ──────────────────────────────────

    def load_model(self) -> None:
        """Pre-warm the fusion_triage singleton (optional — it lazy-loads anyway)."""
        self._load_metadata()
        try:
            from services.fusion_triage import get_model
            model, _ = get_model()
            self._fusion_available = model is not None
            self._loaded = True
            if self._fusion_available:
                logger.info("[SeverityModel] XGBoost fusion model loaded.")
            else:
                logger.warning(
                    "[SeverityModel] XGBoost model not found — rule-based fallback active."
                )
        except Exception as exc:
            logger.error("[SeverityModel] load_model failed: %s", exc)
            self._loaded = True          # mark loaded so we don't retry on every call
            self._fusion_available = False

    def predict(self, features: FeatureVector) -> SeverityPrediction:
        """Run fusion triage and return a typed SeverityPrediction."""
        try:
            return self._run_fusion(features)
        except Exception as exc:
            logger.error("[SeverityModel] predict failed: %s — using emergency fallback.", exc)
            return self._emergency_fallback(features, str(exc))

    def predict_proba(self, features: FeatureVector) -> Dict[str, float]:
        """Return per-class probability dict."""
        pred = self.predict(features)
        if pred.class_probabilities:
            return pred.class_probabilities
        # Derive from confidence on predicted class
        main_prob = pred.confidence
        remainder = round((1.0 - main_prob) / 3, 3)
        result = {c.value: remainder for c in SeverityClass}
        result[pred.severity_class.value] = main_prob
        return result

    def get_model_version(self) -> str:
        return self._model_version

    def health_check(self) -> Dict[str, Any]:
        if not self._loaded:
            self.load_model()
            
        from services.fusion_triage import get_model_error
        err = get_model_error()
            
        if self._fusion_available:
            detail = "XGBoost fusion model loaded."
        elif err:
            detail = err
        else:
            detail = "Rule-based fallback active."
            
        return {
            "status": "ready" if self._fusion_available else "degraded",
            "model_type": "xgboost" if self._fusion_available else "rule_based_fallback",
            "model_version": self._model_version,
            "training_data_type": self._metadata.get("training_dataset_type", "synthetic"),
            "training_sample_count": self._metadata.get("training_sample_count"),
            "trained_at": self._metadata.get("trained_at"),
            "feature_version": self._metadata.get("feature_version", "1.0"),
            "detail": detail,
            "metadata_loaded": bool(self._metadata)
        }

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    # ── Internal helpers ───────────────────────────────────────

    def _run_fusion(self, features: FeatureVector) -> SeverityPrediction:
        """Call fusion_triage.fuse_triage_signals() and map to SeverityPrediction."""
        from services.fusion_triage import fuse_triage_signals

        # Extract the three primary scores; None if the signal was absent
        image_score = features.image.image_severity_score if features.image.image_available else None
        nlp_score = features.audio.nlp_severity_score if features.audio.audio_available else None
        if nlp_score is None and features.text.raw_text_available:
            nlp_score = features.text.nlp_severity_score
        sensor_score = features.sensor_score if features.sensor_available else None
        medical_risk = features.patient.medical_risk_score or 0.5

        result = fuse_triage_signals(
            image_score=image_score,
            nlp_score=nlp_score,
            sensor_score=sensor_score,
            medical_risk=medical_risk,
        )

        # Determine if XGBoost or rule-based was used
        shap_factors_raw = result.get("shap_factors", [])
        is_rule_based = bool(
            shap_factors_raw
            and "Rule-based" in str(shap_factors_raw[0].get("label", ""))
        )
        model_type = "rule_based_fallback" if is_rule_based else "xgboost_fusion"

        # Map P-code → SeverityClass
        p_code = result.get("severity", "P3")
        severity_class = SeverityClass.from_p_code(p_code)

        # Build typed SHAP factors
        shap_factors = []
        for sf in shap_factors_raw:
            if isinstance(sf, dict) and "feature" in sf:
                shap_factors.append(SHAPFactor(
                    feature=sf.get("feature", "unknown"),
                    impact=float(sf.get("impact", 0.0)),
                    direction=sf.get("direction", "increases"),
                    label=sf.get("label", ""),
                ))

        # Build per-class probabilities
        raw_probs = result.get("probabilities", {})
        class_probs: Dict[str, float] = {}
        if raw_probs:
            p_to_class = {"P1": "CRITICAL", "P2": "HIGH", "P3": "MODERATE", "P4": "LOW"}
            class_probs = {p_to_class.get(k, k): v for k, v in raw_probs.items()}

        return SeverityPrediction(
            severity_class=severity_class,
            severity_score=float(result.get("confidence", 0.5)),
            confidence=float(result.get("confidence", 0.5)),
            class_probabilities=class_probs if class_probs else None,
            shap_factors=shap_factors,
            model_version=self._model_version,
            model_type="xgboost" if model_type == "xgboost_fusion" else model_type,
            training_data_type=self._metadata.get("training_dataset_type", "synthetic"),
            feature_version=self._metadata.get("feature_version", "1.0"),
            feature_summary=features.summary_dict(),
            signals_used=result.get("signals_used", {}),
        )

    def _emergency_fallback(self, features: FeatureVector, error: str) -> SeverityPrediction:
        """Last-resort fallback when fusion_triage itself fails."""
        logger.error("[SeverityModel] Emergency fallback triggered: %s", error)
        return SeverityPrediction(
            severity_class=SeverityClass.MODERATE,
            severity_score=0.5,
            confidence=0.3,
            model_version=self._model_version,
            model_type="emergency_fallback",
            training_data_type="synthetic",
            feature_version="1.0",
            feature_summary=features.summary_dict(),
            signals_used={},
            shap_factors=[],
        )


# Module-level singleton
_severity_model: SeverityModel | None = None


def get_severity_model() -> SeverityModel:
    """Return the module-level SeverityModel singleton, loading on first call."""
    global _severity_model
    if _severity_model is None:
        _severity_model = SeverityModel()
        _severity_model.load_model()
    return _severity_model
