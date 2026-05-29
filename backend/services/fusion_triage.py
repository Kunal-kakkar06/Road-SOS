"""
fusion_triage.py — XGBoost multi-signal fusion with SHAP explainability.

Loads fusion_triage.pkl from backend/models/. If the file is absent,
falls back to a deterministic rule-based fusion so the endpoint never crashes.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np

logger = logging.getLogger("roadsos.fusion_triage")

MODEL_PATH = Path(__file__).parent.parent / "models" / "fusion_triage.pkl"

_model     = None
_explainer = None

# ── Severity maps ──────────────────────────────────────────────
SEVERITY_MAP = {0: "P1", 1: "P2", 2: "P3", 3: "P4"}
SEV_LABEL    = {
    "P1": "Critical — immediate dispatch required",
    "P2": "Serious — urgent, within 10 minutes",
    "P3": "Moderate — stable, within 30 minutes",
    "P4": "Minor — self-transport may be appropriate",
}
SEV_COLOR = {
    "P1": "#ba1a1a",
    "P2": "#fca311",
    "P3": "#006687",
    "P4": "#27AE60",
}

FEATURE_NAMES = [
    "image_score", "nlp_score", "sensor_score", "medical_risk",
    "has_image",   "has_nlp",   "has_sensor",
    "mean_signal", "max_signal", "signal_count",
]


def get_model():
    """Lazy-load XGBoost model + SHAP TreeExplainer."""
    global _model, _explainer
    if _model is None:
        if MODEL_PATH.exists():
            try:
                import shap
                _model     = joblib.load(MODEL_PATH)
                _explainer = shap.TreeExplainer(_model)
                logger.info("[FusionTriage] Model loaded from %s", MODEL_PATH)
            except Exception as exc:
                logger.error("[FusionTriage] Failed to load model: %s", exc)
                _model = False          # mark as disabled
        else:
            logger.warning(
                "[FusionTriage] %s not found — using rule-based fallback. "
                "Run backend/data/train_fusion_model.py first.", MODEL_PATH
            )
            _model = False
    return (_model, _explainer) if _model is not False else (None, None)


def _build_features(img: float, nlp: float, sen: float,
                    medical_risk: float,
                    has_img: float, has_nlp: float, has_sen: float) -> np.ndarray:
    mean   = (img + nlp + sen) / 3
    maxv   = max(img, nlp, sen)
    count  = has_img + has_nlp + has_sen
    return np.array([[img, nlp, sen, medical_risk,
                       has_img, has_nlp, has_sen,
                       mean, maxv, count]])


def _extract_shap(shap_vals, sev_idx: int, feature_vals: np.ndarray) -> List[Dict]:
    """Return top-3 SHAP factors with human-readable labels."""
    try:
        if isinstance(shap_vals, list):
            sv = shap_vals[sev_idx][0]
        else:
            sv = shap_vals[sev_idx][0] if shap_vals.ndim == 3 else shap_vals[0]

        sorted_idx = np.argsort(np.abs(sv))[::-1]
        factors    = []
        for i in sorted_idx[:3]:
            feat  = FEATURE_NAMES[i]
            val   = float(feature_vals[0][i])
            impact= float(sv[i])
            factors.append({
                "feature":   feat,
                "impact":    round(abs(impact), 3),
                "direction": "increases" if impact > 0 else "decreases",
                "label":     _human_label(feat, val),
            })
        return factors
    except Exception as exc:
        logger.debug("[SHAP] Could not extract factors: %s", exc)
        return []


def _human_label(feat: str, val: float) -> str:
    labels = {
        "image_score":  f"Injury photo severity score: {val:.2f}",
        "nlp_score":    f"Voice symptom severity score: {val:.2f}",
        "sensor_score": f"Crash sensor severity score: {val:.2f}",
        "max_signal":   f"Worst signal value: {val:.2f}",
        "mean_signal":  f"Average signal severity: {val:.2f}",
        "medical_risk": f"Medical profile vulnerability: {val:.2f}",
        "has_image":    "Injury photo available" if val else "No injury photo",
        "has_nlp":      "Voice recording available" if val else "No voice recording",
        "has_sensor":   "Crash sensor data available" if val else "No sensor data",
        "signal_count": f"{int(val)} of 3 signals available",
    }
    return labels.get(feat, f"{feat}: {val:.2f}")


def _rule_based_fusion(img, nlp, sen, has_img, has_nlp, has_sen) -> Dict:
    """Deterministic fallback when the XGBoost model is not loaded."""
    available = [s for s, h in [(img, has_img), (nlp, has_nlp), (sen, has_sen)] if h]
    mean = sum(available) / len(available) if available else 0.5

    if   mean >= 0.75: sev = "P1"
    elif mean >= 0.55: sev = "P2"
    elif mean >= 0.35: sev = "P3"
    else:              sev = "P4"

    return {
        "severity":       sev,
        "severity_label": SEV_LABEL[sev],
        "severity_color": SEV_COLOR[sev],
        "confidence":     round(mean, 3),
        "probabilities":  {},
        "shap_factors":   [{"label": "Rule-based estimate — XGBoost model not loaded"}],
        "signals_used":   {
            "image":  bool(has_img),
            "nlp":    bool(has_nlp),
            "sensor": bool(has_sen),
        },
    }


# ── Public API ─────────────────────────────────────────────────

def fuse_triage_signals(
    image_score:  Optional[float],
    nlp_score:    Optional[float],
    sensor_score: Optional[float],
    medical_risk: float = 0.5,
) -> Dict:
    """
    Combine available signal scores into a final P1–P4 severity assessment.

    Args:
        image_score  : 0.0–1.0 from EfficientNet (None if no photo)
        nlp_score    : 0.0–1.0 from Whisper/NLP   (None if no voice)
        sensor_score : 0.0–1.0 from crash sensors  (None if not crash)
        medical_risk : 0.0–1.0 from medical profile vulnerability

    Returns:
        severity, severity_label, severity_color, confidence, probabilities,
        shap_factors, signals_used
    """
    img = image_score  if image_score  is not None else 0.5
    nlp = nlp_score    if nlp_score    is not None else 0.5
    sen = sensor_score if sensor_score is not None else 0.5

    has_img = 1.0 if image_score  is not None else 0.0
    has_nlp = 1.0 if nlp_score    is not None else 0.0
    has_sen = 1.0 if sensor_score is not None else 0.0

    model, explainer = get_model()

    if model is None:
        return _rule_based_fusion(img, nlp, sen, has_img, has_nlp, has_sen)

    features = _build_features(
        img, nlp, sen, medical_risk, has_img, has_nlp, has_sen
    )
    probs    = model.predict_proba(features)[0]
    sev_idx  = int(np.argmax(probs))
    severity = SEVERITY_MAP[sev_idx]

    shap_vals = explainer.shap_values(features)
    factors   = _extract_shap(shap_vals, sev_idx, features)

    return {
        "severity":       severity,
        "severity_label": SEV_LABEL[severity],
        "severity_color": SEV_COLOR[severity],
        "confidence":     round(float(probs[sev_idx]), 3),
        "probabilities":  {
            SEVERITY_MAP[i]: round(float(p), 3)
            for i, p in enumerate(probs)
        },
        "shap_factors":   factors,
        "signals_used":   {
            "image":  bool(has_img),
            "nlp":    bool(has_nlp),
            "sensor": bool(has_sen),
        },
    }
