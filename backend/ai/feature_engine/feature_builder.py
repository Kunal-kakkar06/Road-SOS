"""
ai/feature_engine/feature_builder.py
======================================
Assembles a complete FeatureVector from an AIInput by coordinating
all individual feature extractors.

The FeatureBuilder is the single entry-point for the model layer.
It guarantees that every field is either a valid value OR explicitly None —
never a silently invented default.
"""

from __future__ import annotations

import logging
from typing import Optional

from ai.schemas.input_schema import AIInput
from ai.schemas.feature_schema import (
    AudioFeatures,
    FeatureVector,
    ImageFeatures,
    LocationFeatures,
    PatientFeatures,
    TextFeatures,
)
from .text_features import extract_text_features, extract_patient_features
from .audio_features import extract_audio_features
from .image_features import extract_image_features

logger = logging.getLogger("roadsos.ai.feature_engine.builder")


class FeatureBuilder:
    """
    Coordinates feature extraction from a single AIInput.

    Usage:
        builder = FeatureBuilder()
        features = builder.build(ai_input)
    """

    def build(self, ai_input: AIInput) -> FeatureVector:
        """
        Extract and assemble a FeatureVector from the given AIInput.

        Each extractor is called independently so a failure in one
        does NOT block the others.  Failed extractors return a safe
        empty sub-schema with available=False.
        """
        logger.debug(
            "[FeatureBuilder] Building features for request_id=%s", ai_input.request_id
        )

        # ── Text / symptom features ───────────────────────────
        try:
            text_features = extract_text_features(ai_input)
        except Exception as exc:
            logger.error("[FeatureBuilder] text_features failed: %s", exc)
            text_features = TextFeatures(raw_text_available=False)

        # ── Patient / demographic features ────────────────────
        try:
            patient_features = extract_patient_features(ai_input)
        except Exception as exc:
            logger.error("[FeatureBuilder] patient_features failed: %s", exc)
            patient_features = PatientFeatures()

        # ── Audio features ────────────────────────────────────
        try:
            audio_features = extract_audio_features(ai_input)
        except Exception as exc:
            logger.error("[FeatureBuilder] audio_features failed: %s", exc)
            audio_features = AudioFeatures(audio_available=False)

        # ── Image features ────────────────────────────────────
        try:
            image_features = extract_image_features(ai_input)
        except Exception as exc:
            logger.error("[FeatureBuilder] image_features failed: %s", exc)
            image_features = ImageFeatures(image_available=False)

        # ── Location features ─────────────────────────────────
        location_features = self._extract_location_features(ai_input)

        # ── Sensor data ───────────────────────────────────────
        sensor_available = ai_input.has_sensor_data and ai_input.sensor_score is not None
        sensor_score: Optional[float] = ai_input.sensor_score if sensor_available else None

        # ── Signal count ──────────────────────────────────────
        signal_count = sum([
            text_features.raw_text_available,
            audio_features.audio_available,
            image_features.image_available,
            sensor_available,
        ])

        vector = FeatureVector(
            text=text_features,
            patient=patient_features,
            audio=audio_features,
            image=image_features,
            location=location_features,
            sensor_available=sensor_available,
            sensor_score=sensor_score,
            signal_count=signal_count,
        )

        logger.debug(
            "[FeatureBuilder] Done — signals=%d, summary=%s",
            signal_count,
            vector.summary_dict(),
        )
        return vector

    def _extract_location_features(self, ai_input: AIInput) -> LocationFeatures:
        """Extract location features from AIInput."""
        has_location = (
            ai_input.latitude is not None and ai_input.longitude is not None
        )
        return LocationFeatures(
            latitude=ai_input.latitude,
            longitude=ai_input.longitude,
            has_location=has_location,
            # distance/travel_time populated later by hospital_ranker
            distance_to_nearest_hospital_km=None,
            nearest_hospital_name=None,
            estimated_travel_time_minutes=None,
        )
