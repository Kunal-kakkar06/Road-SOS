"""
ai/schemas/input_schema.py
==========================
Unified AI input contract.

All fields are Optional so the pipeline can work with partial data
(text-only, voice-only, image-only, or any combination).  The pipeline
must never silently invent values for missing fields.

This schema is NOT the public FastAPI request model — existing
/api/triage endpoints keep their own request models unchanged.
AIInput is the internal canonical form that the orchestrator works with.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class AIInput(BaseModel):
    """Canonical internal input to the AI pipeline."""

    # ── Identity ──────────────────────────────────────────────
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique ID for this inference request (caller-generated or auto).",
    )
    user_id: Optional[str] = Field(
        None, description="User UUID — used for medical profile lookup."
    )
    incident_id: Optional[str] = Field(
        None, description="Linked incident UUID if this triage is associated with a crash/SOS."
    )

    # ── Text / symptoms ───────────────────────────────────────
    symptoms: Optional[str] = Field(
        None, description="Free-text symptom description entered by the user."
    )

    # ── Patient demographics ──────────────────────────────────
    age: Optional[int] = Field(None, ge=0, le=130)
    gender: Optional[str] = Field(None)
    pain_level: Optional[int] = Field(None, ge=1, le=10)
    consciousness: Optional[str] = Field(
        None, description="e.g. 'Alert', 'Unresponsive', 'Voice response'."
    )
    breathing: Optional[str] = Field(
        None, description="e.g. 'Normal', 'Labored', 'Absent', 'Rapid'."
    )

    # ── Medical profile (pre-loaded from DB) ──────────────────
    medical_profile: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Serialised MedicalProfile dict with keys: blood_type, allergies, "
            "medications, conditions, disabilities."
        ),
    )

    # ── Pre-computed signal scores (from existing services) ───
    # These are 0.0–1.0 floats produced by nlp_triage / image_triage / crash_ml
    # before the orchestrator is called.  None = signal not available.
    voice_transcript: Optional[str] = Field(
        None, description="Whisper/STT transcript (if voice was provided)."
    )
    nlp_score: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="NLP severity score from nlp_triage service (0=low, 1=critical).",
    )
    image_score: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="Injury image severity score from image_triage service.",
    )
    sensor_score: Optional[float] = Field(
        None, ge=0.0, le=1.0,
        description="Crash sensor severity score from crash_ml service.",
    )

    # Convenience flags (derived from the above — set by caller)
    has_voice: bool = Field(False)
    has_image: bool = Field(False)
    has_sensor_data: bool = Field(False)

    # ── Location ──────────────────────────────────────────────
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)

    # ── Context ───────────────────────────────────────────────
    timestamp: Optional[str] = Field(
        None, description="ISO-8601 timestamp of the emergency event."
    )
    was_offline: bool = Field(
        False, description="True if the data was collected while the device was offline."
    )

    @validator("pain_level", pre=True)
    def clamp_pain(cls, v):  # noqa: N805
        if v is None:
            return v
        return max(1, min(10, int(v)))

    class Config:
        # Allow extra fields to be ignored — future-proofs against callers
        # passing additional keys without breaking validation.
        extra = "ignore"
