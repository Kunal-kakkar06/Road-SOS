"""
ai/decision/severity_service.py
================================
Translates a SeverityPrediction into display-ready metadata.

This is a thin stateless adapter — it does not make new predictions,
it only enriches the prediction with labels, colors, and ETA estimates
consistent with the rest of the RoadSOS UI.
"""

from __future__ import annotations

from ai.schemas.prediction_schema import SeverityClass, SeverityPrediction


# ETA estimates by severity class (minutes)
_ETA_MAP = {
    SeverityClass.CRITICAL: 6,
    SeverityClass.HIGH: 15,
    SeverityClass.MODERATE: 25,
    SeverityClass.LOW: 45,
}

# Priority labels
_PRIORITY_MAP = {
    SeverityClass.CRITICAL: "IMMEDIATE",
    SeverityClass.HIGH: "URGENT",
    SeverityClass.MODERATE: "STANDARD",
    SeverityClass.LOW: "MONITOR",
}


class SeverityService:
    """
    Stateless adapter: SeverityPrediction → display metadata.

    No ML inference happens here.  This class only reads the prediction
    and returns derived display attributes.
    """

    @staticmethod
    def get_eta_minutes(prediction: SeverityPrediction) -> int:
        return _ETA_MAP.get(prediction.severity_class, 25)

    @staticmethod
    def get_priority(prediction: SeverityPrediction) -> str:
        return _PRIORITY_MAP.get(prediction.severity_class, "STANDARD")

    @staticmethod
    def get_display_label(prediction: SeverityPrediction) -> str:
        return prediction.severity_class.to_display_label()

    @staticmethod
    def get_color(prediction: SeverityPrediction) -> str:
        return prediction.severity_class.to_color()

    @staticmethod
    def get_p_code(prediction: SeverityPrediction) -> str:
        """Return the P1/P2/P3/P4 code used by existing services."""
        return prediction.severity_class.to_p_code()

    @staticmethod
    def requires_emergency_dispatch(prediction: SeverityPrediction) -> bool:
        return prediction.severity_class in (SeverityClass.CRITICAL, SeverityClass.HIGH)

    @staticmethod
    def requires_responder(prediction: SeverityPrediction) -> bool:
        return prediction.severity_class == SeverityClass.CRITICAL
