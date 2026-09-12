"""
ai/schemas/decision_schema.py
==============================
Decision and unified response schemas.

EmergencyDecision:  what the system recommends (actions, priorities)
UnifiedAIResponse:  the complete top-level response from the orchestrator
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .prediction_schema import SeverityPrediction


class EmergencyDecision(BaseModel):
    """
    Structured emergency action recommendation.

    Produced by the decision engine from a SeverityPrediction.
    Uses rule-based logic — NOT LLM-generated — so it is deterministic
    and safe for emergency contexts.
    """

    priority: str = Field(
        description="'IMMEDIATE', 'URGENT', 'STANDARD', or 'MONITOR'."
    )
    recommended_action: str = Field(
        description="Primary recommended action in plain language."
    )
    actions: List[str] = Field(
        default_factory=list,
        description="Ordered list of step-by-step recommended actions.",
    )
    hospital_required: bool
    emergency_contact_required: bool
    responder_required: bool
    estimated_eta_minutes: Optional[int] = Field(
        None,
        description="Estimated emergency response arrival time based on severity.",
    )
    reasoning: str = Field(
        description=(
            "Brief explanation of why this decision was reached. "
            "Based on severity class and rule set — not LLM output."
        )
    )

    # Safety disclaimer — always present
    disclaimer: str = Field(
        default=(
            "This is a risk estimate for decision support only. "
            "It is not a medical diagnosis. Always seek professional "
            "emergency assistance when in doubt."
        )
    )


class HospitalRecommendation(BaseModel):
    """A single ranked hospital recommendation."""

    rank: int
    hospital_id: Optional[str] = None
    name: str
    address: Optional[str] = None
    distance_km: Optional[float] = None
    estimated_travel_minutes: Optional[float] = None
    has_trauma_center: Optional[bool] = None
    has_cath_lab: Optional[bool] = None
    trauma_beds_available: Optional[int] = None
    icu_beds_available: Optional[int] = None
    ranking_score: Optional[float] = None


class RAGSource(BaseModel):
    """A single retrieved document/chunk from the RAG system."""

    source_id: str
    title: Optional[str] = None
    content: str
    relevance_score: Optional[float] = None
    source_type: Optional[str] = None  # e.g. "medical_guideline", "protocol"


class ProcessingMetadata(BaseModel):
    """Operational metadata about how this request was processed."""

    stages_completed: List[str] = Field(default_factory=list)
    stages_failed: List[str] = Field(default_factory=list)
    processing_time_ms: Optional[float] = None
    model_fallback_used: bool = False
    rag_used: bool = False
    llm_used: bool = False
    errors: List[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal errors encountered during processing. "
            "Fatal errors raise exceptions instead."
        ),
    )


class UnifiedAIResponse(BaseModel):
    """
    Top-level response from AIOrchestrator.process().

    This is the internal response object.  It is NOT directly the
    API response — routers map it to their own response models to
    preserve existing API contracts.
    """

    request_id: str

    # Core outputs
    prediction: SeverityPrediction
    decision: EmergencyDecision

    # Optional enrichments (may be absent if components are unavailable)
    hospital_recommendations: List[HospitalRecommendation] = Field(
        default_factory=list
    )
    retrieved_sources: List[RAGSource] = Field(default_factory=list)
    explanation: Optional[str] = Field(
        None,
        description=(
            "Natural-language explanation from LLM. None if LLM is disabled "
            "or unavailable — prediction and decision still stand."
        ),
    )

    # Provenance
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
    processing_metadata: ProcessingMetadata = Field(
        default_factory=ProcessingMetadata
    )
