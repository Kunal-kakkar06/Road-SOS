"""
ai/decision/emergency_decision.py
===================================
Converts a SeverityPrediction into a structured EmergencyDecision.

All decision logic is deterministic and rule-based.
No LLM calls occur here — the LLM is an OPTIONAL downstream step
that generates a human-readable explanation after the decision is made.

Rules are defined in _SEVERITY_RULES below.  They can be extended
without changing the orchestrator or any other component.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from ai.schemas.decision_schema import EmergencyDecision
from ai.schemas.prediction_schema import SeverityClass, SeverityPrediction
from .severity_service import SeverityService

logger = logging.getLogger("roadsos.ai.decision.engine")


# ── Decision rules per severity class ─────────────────────────────
# Format: {SeverityClass: (recommended_action, actions_list, eta_min,
#           hospital_required, emergency_contact_required, responder_required)}
_SEVERITY_RULES: Dict[SeverityClass, dict] = {
    SeverityClass.CRITICAL: {
        "recommended_action": "Call emergency services immediately and request an ambulance.",
        "actions": [
            "🚨 Call emergency services immediately and request an ambulance.",
            "Do not leave the patient alone.",
            "Keep the patient warm, still, and calm.",
            "Monitor breathing — be ready to perform CPR if breathing stops.",
            "Share the patient's location and medical profile with responders.",
        ],
        "hospital_required": True,
        "emergency_contact_required": True,
        "responder_required": True,
        "reasoning": (
            "Severity is CRITICAL (P1). Immediate professional medical intervention is required."
        ),
    },
    SeverityClass.HIGH: {
        "recommended_action": "Seek urgent medical attention at the nearest emergency department.",
        "actions": [
            "Seek urgent medical attention at the nearest emergency department.",
            "Call emergency services or arrange transport immediately.",
            "Keep the patient calm, still, and monitored.",
            "Apply basic first aid for visible injuries (bleeding, fractures).",
        ],
        "hospital_required": True,
        "emergency_contact_required": True,
        "responder_required": False,
        "reasoning": (
            "Severity is HIGH (P2). Urgent professional medical evaluation is required within 10 minutes."
        ),
    },
    SeverityClass.MODERATE: {
        "recommended_action": "Arrange medical evaluation at an urgent care clinic or hospital.",
        "actions": [
            "Arrange medical evaluation at an urgent care clinic or hospital.",
            "Monitor the patient's condition closely.",
            "Notify an emergency contact.",
            "Seek immediate help if symptoms worsen.",
        ],
        "hospital_required": True,
        "emergency_contact_required": False,
        "responder_required": False,
        "reasoning": (
            "Severity is MODERATE (P3). Medical evaluation recommended within 30 minutes."
        ),
    },
    SeverityClass.LOW: {
        "recommended_action": "Monitor symptoms at home and seek help if they worsen.",
        "actions": [
            "Ensure the patient is in a safe and comfortable environment.",
            "Monitor vital signs (breathing, responsiveness) continuously.",
            "Rest and monitor symptoms; seek medical advice if they worsen.",
            "Schedule a visit to a primary care doctor if symptoms persist.",
        ],
        "hospital_required": False,
        "emergency_contact_required": False,
        "responder_required": False,
        "reasoning": (
            "Severity is LOW (P4). Condition appears minor — monitor and seek help if anything changes."
        ),
    },
}

_DISCLAIMER = (
    "This is a risk estimate for decision support only. "
    "It is not a medical diagnosis. Always seek professional "
    "emergency assistance when in doubt."
)


class EmergencyDecisionEngine:
    """
    Converts a SeverityPrediction into a structured EmergencyDecision.

    Stateless — create once and call make_decision() for each request.
    """

    def make_decision(self, prediction: SeverityPrediction) -> EmergencyDecision:
        """
        Apply severity rules to produce an EmergencyDecision.

        Never raises — falls back to MODERATE rules on unexpected input.
        """
        try:
            rules = _SEVERITY_RULES.get(prediction.severity_class, _SEVERITY_RULES[SeverityClass.MODERATE])
            eta = SeverityService.get_eta_minutes(prediction)
            priority = SeverityService.get_priority(prediction)

            return EmergencyDecision(
                priority=priority,
                recommended_action=rules["recommended_action"],
                actions=list(rules["actions"]),
                hospital_required=rules["hospital_required"],
                emergency_contact_required=rules["emergency_contact_required"],
                responder_required=rules["responder_required"],
                estimated_eta_minutes=eta,
                reasoning=rules["reasoning"],
                disclaimer=_DISCLAIMER,
            )
        except Exception as exc:
            logger.error("[DecisionEngine] make_decision failed: %s — using MODERATE fallback.", exc)
            return self._fallback_decision()

    def _fallback_decision(self) -> EmergencyDecision:
        """Safe fallback decision when something unexpected goes wrong."""
        return EmergencyDecision(
            priority="STANDARD",
            recommended_action="Seek medical evaluation as a precaution.",
            actions=[
                "Seek medical evaluation as a precaution.",
                "Monitor the patient's condition.",
                "Contact emergency services if the condition worsens.",
            ],
            hospital_required=True,
            emergency_contact_required=False,
            responder_required=False,
            estimated_eta_minutes=25,
            reasoning="Decision engine encountered an error — conservative MODERATE defaults applied.",
            disclaimer=_DISCLAIMER,
        )
