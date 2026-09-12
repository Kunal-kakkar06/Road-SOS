"""
ai/feature_engine/image_features.py
=====================================
Extracts ImageFeatures from injury image input.

Wraps the existing services.image_triage.score_injury_image() so the
feature engine never re-implements vision logic.  If the image service
is unavailable, returns image_available=False with explicit None values.
"""

from __future__ import annotations

import logging

from ai.schemas.input_schema import AIInput
from ai.schemas.feature_schema import ImageFeatures

logger = logging.getLogger("roadsos.ai.feature_engine.image")


def extract_image_features(ai_input: AIInput) -> ImageFeatures:
    """
    Extract ImageFeatures from AIInput.

    Current triage workflow: the router calls image_triage.score_injury_image()
    and stores the resulting score in AIInput.image_score.  We use that
    pre-computed value directly to avoid double-processing.

    Future: when image bytes are passed through the pipeline, this function
    will call score_injury_image() directly.
    """
    if not ai_input.has_image:
        return ImageFeatures(image_available=False)

    # Pre-computed score placed by the calling router
    score = ai_input.image_score
    if score is None:
        logger.warning(
            "[ImageFeatures] has_image=True but image_score is None — "
            "signal will be treated as unavailable."
        )
        return ImageFeatures(image_available=False)

    # Map 0.0–1.0 score to confidence tier
    if score >= 0.70:
        confidence = "high"
    elif score >= 0.50:
        confidence = "medium"
    else:
        confidence = "low"

    return ImageFeatures(
        image_available=True,
        image_severity_score=score,
        image_confidence=confidence,
        probabilities=None,  # probabilities not carried through pre-computed path
    )
