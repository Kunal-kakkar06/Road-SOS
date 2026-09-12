"""
ai/feature_engine/audio_features.py
=====================================
Extracts AudioFeatures from voice input.

Wraps the existing services.nlp_triage.score_voice_input() so the
feature engine never re-implements NLP logic.  If the voice service
is unavailable, returns audio_available=False with explicit None values.
"""

from __future__ import annotations

import logging
from typing import Optional

from ai.schemas.input_schema import AIInput
from ai.schemas.feature_schema import AudioFeatures

logger = logging.getLogger("roadsos.ai.feature_engine.audio")


def extract_audio_features(ai_input: AIInput) -> AudioFeatures:
    """
    Extract AudioFeatures from AIInput.

    If a pre-computed nlp_score and transcript already exist on the input
    (placed there by the triage router which called nlp_triage itself),
    we use those values directly without re-processing audio bytes.

    If only raw audio is available (future: passed as bytes ref), we
    would call score_voice_input here.  For now the triage router pre-
    processes voice and stores the score + transcript in AIInput.
    """
    # Case 1: pre-computed (current workflow — router pre-processes voice)
    if ai_input.has_voice:
        return AudioFeatures(
            audio_available=True,
            transcript=ai_input.voice_transcript,
            nlp_severity_score=ai_input.nlp_score,
            keywords_hit=None,  # not available from pre-computed path
        )

    # Case 2: voice transcript provided but no pre-computed score
    if ai_input.voice_transcript and not ai_input.has_voice:
        try:
            from services.nlp_triage import extract_severity_from_text
            result = extract_severity_from_text(ai_input.voice_transcript)
            return AudioFeatures(
                audio_available=True,
                transcript=ai_input.voice_transcript,
                nlp_severity_score=result.get("score"),
                keywords_hit=result.get("keywords_hit"),
            )
        except Exception as exc:
            logger.warning("[AudioFeatures] nlp_triage unavailable: %s", exc)
            return AudioFeatures(
                audio_available=True,
                transcript=ai_input.voice_transcript,
                nlp_severity_score=None,
                keywords_hit=None,
            )

    # Case 3: no audio data
    return AudioFeatures(audio_available=False)
