"""
ai/feature_engine/text_features.py
====================================
Extracts TextFeatures and PatientFeatures from an AIInput.

Delegates to the new ai.feature_engine.nlp_service module for semantic
text extraction. If unavailable, returns explicit None values rather
than invented fallbacks.
"""

from __future__ import annotations

import logging
from typing import Optional

from ai.schemas.input_schema import AIInput
from ai.schemas.feature_schema import TextFeatures, PatientFeatures

logger = logging.getLogger("roadsos.ai.feature_engine.text")

# Consciousness → severity score mapping (higher = more severe)
_CONSCIOUSNESS_MAP = {
    "alert": 0.0,
    "voice response": 0.3,
    "pain response": 0.6,
    "unresponsive": 1.0,
}

# Breathing → severity score mapping
_BREATHING_MAP = {
    "normal": 0.0,
    "rapid": 0.4,
    "labored": 0.6,
    "shallow": 0.5,
    "absent": 1.0,
}

# Conditions that raise medical risk
_HIGH_RISK_CONDITIONS = {
    "diabetes", "hypertension", "heart disease", "cardiac",
    "asthma", "copd", "epilepsy", "kidney disease", "liver disease",
}
_CARDIAC_KEYWORDS = {"heart", "cardiac", "coronary", "angina"}
_RESPIRATORY_KEYWORDS = {"asthma", "copd", "lung", "respiratory", "breathing"}


def extract_text_features(ai_input: AIInput) -> TextFeatures:
    """
    Extract TextFeatures from the text/symptom portion of AIInput.

    If a pre-computed nlp_score already exists on the input (placed there
    by the calling router), we use it directly.  Otherwise we call the
    nlp_triage service inline.
    """
    if not ai_input.symptoms and ai_input.nlp_score is None:
        return TextFeatures(raw_text_available=False)

    # Use pre-computed score if provided by caller
    if ai_input.nlp_score is not None:
        return TextFeatures(
            raw_text_available=bool(ai_input.symptoms),
            nlp_severity_score=ai_input.nlp_score,
            symptom_count=len([s.strip() for s in (ai_input.symptoms or "").split(",") if s.strip()]) if ai_input.symptoms else None
        )
    else:
        try:
            from ai.feature_engine.nlp_service import extract_features
            return extract_features(ai_input.symptoms or "")
        except Exception as exc:
            logger.warning("[TextFeatures] nlp_service unavailable: %s", exc)
            return TextFeatures(
                raw_text_available=bool(ai_input.symptoms),
                nlp_severity_score=None
            )


def extract_patient_features(ai_input: AIInput) -> PatientFeatures:
    """
    Extract PatientFeatures from demographics + medical profile.

    All values are Optional — missing → None (not invented).
    """
    profile = ai_input.medical_profile or {}

    # Age
    age = ai_input.age
    if age is None and profile.get("date_of_birth"):
        try:
            from datetime import date
            dob = profile["date_of_birth"]
            # Support YYYY-MM-DD or DD/MM/YYYY
            if "/" in str(dob):
                parts = str(dob).split("/")
                birth_year = int(parts[2]) if len(parts) == 3 else None
            else:
                birth_year = int(str(dob)[:4])
            if birth_year:
                age = date.today().year - birth_year
        except Exception:
            age = None

    # Gender encoding: 0.0=male, 1.0=female, 0.5=unknown
    gender_raw = (ai_input.gender or profile.get("gender") or "").lower()
    gender_encoded: Optional[float]
    if "male" in gender_raw and "fe" not in gender_raw:
        gender_encoded = 0.0
    elif "female" in gender_raw or "woman" in gender_raw:
        gender_encoded = 1.0
    else:
        gender_encoded = None

    # Medical conditions
    conditions: list = profile.get("conditions") or []
    conditions_lower = " ".join(str(c).lower() for c in conditions)
    medications: list = profile.get("medications") or []
    allergies: list = profile.get("allergies") or []

    has_diabetes = any("diabet" in str(c).lower() for c in conditions) or None
    has_hypertension = any("hypertension" in str(c).lower() or "blood pressure" in str(c).lower() for c in conditions) or None
    has_cardiac = any(k in conditions_lower for k in _CARDIAC_KEYWORDS) or None
    has_respiratory = any(k in conditions_lower for k in _RESPIRATORY_KEYWORDS) or None

    # Force None (not False) when no profile was provided
    if not conditions:
        has_diabetes = None
        has_hypertension = None
        has_cardiac = None
        has_respiratory = None

    # Medical risk score: composite 0.0–1.0
    medical_risk: Optional[float] = None
    if conditions or medications or allergies:
        risk = 0.3  # baseline for having a known condition
        if has_diabetes:
            risk += 0.1
        if has_hypertension:
            risk += 0.1
        if has_cardiac:
            risk += 0.15
        if has_respiratory:
            risk += 0.1
        risk += min(0.1, len(medications) * 0.02)
        medical_risk = round(min(1.0, risk), 3)

    # Consciousness encoding
    consciousness_score: Optional[float] = None
    if ai_input.consciousness:
        c_lower = ai_input.consciousness.lower().strip()
        consciousness_score = _CONSCIOUSNESS_MAP.get(c_lower)
        if consciousness_score is None:
            # Fuzzy match
            for k, v in _CONSCIOUSNESS_MAP.items():
                if k in c_lower:
                    consciousness_score = v
                    break

    # Breathing encoding
    breathing_score: Optional[float] = None
    if ai_input.breathing:
        b_lower = ai_input.breathing.lower().strip()
        breathing_score = _BREATHING_MAP.get(b_lower)
        if breathing_score is None:
            for k, v in _BREATHING_MAP.items():
                if k in b_lower:
                    breathing_score = v
                    break

    # Pain level normalised to 0.0–1.0
    pain_normalised: Optional[float] = None
    if ai_input.pain_level is not None:
        pain_normalised = round((ai_input.pain_level - 1) / 9.0, 3)

    return PatientFeatures(
        age=age,
        gender_encoded=gender_encoded,
        has_diabetes=has_diabetes,
        has_hypertension=has_hypertension,
        has_cardiac_condition=has_cardiac,
        has_respiratory_condition=has_respiratory,
        allergy_count=len(allergies) if allergies else None,
        medication_count=len(medications) if medications else None,
        medical_risk_score=medical_risk,
        consciousness_score=consciousness_score,
        breathing_score=breathing_score,
        pain_level_normalised=pain_normalised,
    )
