"""
tests/ai/test_decision_engine.py
Tests for EmergencyDecisionEngine and SeverityService.
"""
import pytest
from ai.decision.emergency_decision import EmergencyDecisionEngine
from ai.decision.severity_service import SeverityService
from ai.schemas.prediction_schema import SeverityClass, SeverityPrediction


def make_prediction(severity: SeverityClass, confidence=0.85) -> SeverityPrediction:
    return SeverityPrediction(
        severity_class=severity,
        severity_score=confidence,
        confidence=confidence,
        model_version="test",
        model_type="mock",
        feature_summary={},
    )


class TestEmergencyDecisionEngine:
    def setup_method(self):
        self.engine = EmergencyDecisionEngine()

    def test_critical_requires_responder(self):
        pred = make_prediction(SeverityClass.CRITICAL)
        dec = self.engine.make_decision(pred)
        assert dec.responder_required is True
        assert dec.hospital_required is True
        assert dec.emergency_contact_required is True
        assert dec.priority == "IMMEDIATE"

    def test_high_no_responder_but_hospital_required(self):
        pred = make_prediction(SeverityClass.HIGH)
        dec = self.engine.make_decision(pred)
        assert dec.responder_required is False
        assert dec.hospital_required is True
        assert dec.priority == "URGENT"

    def test_moderate_decision(self):
        pred = make_prediction(SeverityClass.MODERATE)
        dec = self.engine.make_decision(pred)
        assert dec.hospital_required is True
        assert dec.responder_required is False
        assert dec.priority == "STANDARD"

    def test_low_no_dispatch(self):
        pred = make_prediction(SeverityClass.LOW)
        dec = self.engine.make_decision(pred)
        assert dec.hospital_required is False
        assert dec.responder_required is False
        assert dec.priority == "MONITOR"

    def test_decision_has_disclaimer(self):
        pred = make_prediction(SeverityClass.MODERATE)
        dec = self.engine.make_decision(pred)
        assert "decision support" in dec.disclaimer.lower() or "not a medical diagnosis" in dec.disclaimer.lower()

    def test_decision_has_actions(self):
        for sev in SeverityClass:
            pred = make_prediction(sev)
            dec = self.engine.make_decision(pred)
            assert len(dec.actions) >= 2

    def test_decision_has_eta(self):
        pred = make_prediction(SeverityClass.CRITICAL)
        dec = self.engine.make_decision(pred)
        assert dec.estimated_eta_minutes is not None
        assert dec.estimated_eta_minutes < 10

    def test_engine_never_raises(self):
        """Even with a completely unexpected severity, engine must not raise."""
        import unittest.mock as mock
        pred = make_prediction(SeverityClass.MODERATE)
        # Simulate _SEVERITY_RULES being broken
        with mock.patch("ai.decision.emergency_decision._SEVERITY_RULES", {}):
            dec = self.engine.make_decision(pred)
        assert dec is not None
        assert dec.priority is not None


class TestSeverityService:
    def test_critical_priority(self):
        pred = make_prediction(SeverityClass.CRITICAL)
        assert SeverityService.get_priority(pred) == "IMMEDIATE"

    def test_eta_increases_with_severity(self):
        critical_eta = SeverityService.get_eta_minutes(make_prediction(SeverityClass.CRITICAL))
        low_eta = SeverityService.get_eta_minutes(make_prediction(SeverityClass.LOW))
        assert critical_eta < low_eta

    def test_requires_emergency_dispatch_critical_and_high(self):
        assert SeverityService.requires_emergency_dispatch(make_prediction(SeverityClass.CRITICAL))
        assert SeverityService.requires_emergency_dispatch(make_prediction(SeverityClass.HIGH))
        assert not SeverityService.requires_emergency_dispatch(make_prediction(SeverityClass.MODERATE))

    def test_get_color_returns_string(self):
        for sev in SeverityClass:
            color = SeverityService.get_color(make_prediction(sev))
            assert color.startswith("#")

    def test_get_p_code(self):
        assert SeverityService.get_p_code(make_prediction(SeverityClass.CRITICAL)) == "P1"
        assert SeverityService.get_p_code(make_prediction(SeverityClass.LOW)) == "P4"
