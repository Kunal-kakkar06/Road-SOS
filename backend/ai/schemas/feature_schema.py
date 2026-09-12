"""
ai/schemas/feature_schema.py
=============================
Internal feature vector representation.

ALL fields are explicitly Optional.  If a signal is not available the
field is None — we NEVER silently fill in a default value that would
make the model think a signal exists when it does not.

This schema bridges the feature_engine (extraction) and the ML model
(inference).  It is never exposed as a public API response.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TextFeatures(BaseModel):
    """Features derived from free-text symptom input."""

    symptom_count: Optional[int] = Field(
        None, description="Number of distinct symptom tokens found."
    )
    emergency_keyword_count: Optional[int] = Field(
        None, description="Number of high-priority emergency keywords detected."
    )
    serious_keyword_count: Optional[int] = Field(
        None, description="Number of serious-severity keywords detected."
    )
    moderate_keyword_count: Optional[int] = Field(
        None, description="Number of moderate-severity keywords detected."
    )
    # Normalised NLP severity score produced by nlp_triage service
    nlp_severity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    raw_text_available: bool = False

    # New detailed indicators requested
    bleeding_indicator: Optional[float] = None
    breathing_difficulty_indicator: Optional[float] = None
    unconsciousness_indicator: Optional[float] = None
    trauma_indicator: Optional[float] = None
    fire_indicator: Optional[float] = None
    trapped_indicator: Optional[float] = None
    chest_pain_indicator: Optional[float] = None
    accident_indicator: Optional[float] = None
    pain_severity_indicator: Optional[float] = None
    urgency_indicator: Optional[float] = None


class PatientFeatures(BaseModel):
    """Features derived from patient demographics and medical profile."""

    age: Optional[int] = None
    gender_encoded: Optional[float] = Field(
        None, description="0.0 = male, 1.0 = female, 0.5 = unknown/other."
    )
    # Condition risk modifiers (each present → increases vulnerability score)
    has_diabetes: Optional[bool] = None
    has_hypertension: Optional[bool] = None
    has_cardiac_condition: Optional[bool] = None
    has_respiratory_condition: Optional[bool] = None
    allergy_count: Optional[int] = None
    medication_count: Optional[int] = None
    # Composite 0.0–1.0 medical vulnerability score (used by fusion model)
    medical_risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    # Derived consciousness/breathing encodings
    consciousness_score: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="1.0 = unresponsive (most severe), 0.0 = fully alert.",
    )
    breathing_score: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="1.0 = absent breathing (most severe), 0.0 = normal.",
    )
    pain_level_normalised: Optional[float] = Field(None, ge=0.0, le=1.0)


class AudioFeatures(BaseModel):
    """Features derived from voice input."""

    audio_available: bool = False
    transcript: Optional[str] = None
    nlp_severity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    keywords_hit: Optional[int] = None


class ImageFeatures(BaseModel):
    """Features derived from injury image."""

    image_available: bool = False
    image_severity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    image_confidence: Optional[str] = Field(
        None, description="'high' | 'medium' | 'low'"
    )
    probabilities: Optional[Dict[str, float]] = Field(
        None, description="Per-class probabilities: P1, P2, P3, P4."
    )


class LocationFeatures(BaseModel):
    """Features derived from geolocation."""

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    has_location: bool = False
    # Populated by hospital_ranker when hospitals are available
    distance_to_nearest_hospital_km: Optional[float] = None
    nearest_hospital_name: Optional[str] = None
    estimated_travel_time_minutes: Optional[float] = None


class FeatureVector(BaseModel):
    """
    Complete internal feature representation fed to the ML model.

    Composed from all available input signals.  Absent signals are None —
    the model and fallback logic handle missing features explicitly.
    """

    text: TextFeatures = Field(default_factory=TextFeatures)
    patient: PatientFeatures = Field(default_factory=PatientFeatures)
    audio: AudioFeatures = Field(default_factory=AudioFeatures)
    image: ImageFeatures = Field(default_factory=ImageFeatures)
    location: LocationFeatures = Field(default_factory=LocationFeatures)

    # Sensor data
    sensor_available: bool = False
    sensor_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Summary flags used by fusion model
    signal_count: int = Field(0, description="How many of text/audio/image/sensor are present.")

    def summary_dict(self) -> dict:
        """Compact representation for logging and response metadata."""
        return {
            "has_text": self.text.raw_text_available,
            "has_audio": self.audio.audio_available,
            "has_image": self.image.image_available,
            "has_sensor": self.sensor_available,
            "signal_count": self.signal_count,
            "nlp_score": self.text.nlp_severity_score,
            "image_score": self.image.image_severity_score,
            "sensor_score": self.sensor_score,
            "medical_risk": self.patient.medical_risk_score,
        }
