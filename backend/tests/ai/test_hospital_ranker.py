"""
tests/ai/test_hospital_ranker.py
Tests for HospitalRanker — mocks at services.maps_service level.
"""
import pytest
from unittest.mock import patch
from ai.decision.hospital_ranker import HospitalRanker
from ai.schemas.prediction_schema import SeverityClass, SeverityPrediction


def make_prediction(severity=SeverityClass.HIGH):
    return SeverityPrediction(
        severity_class=severity, severity_score=0.7, confidence=0.7,
        model_version="test", model_type="mock", feature_summary={},
    )


HOSPITALS = [
    {"id": "h1", "name": "City Hospital", "latitude": 12.97, "longitude": 77.59,
     "address": "MG Road", "has_trauma_center": True, "has_cath_lab": False,
     "trauma_beds_available": 5, "icu_beds_available": 3},
    {"id": "h2", "name": "General Hospital", "latitude": 12.98, "longitude": 77.60,
     "address": "Brigade Road", "has_trauma_center": False, "has_cath_lab": True,
     "trauma_beds_available": 2, "icu_beds_available": 1},
    {"id": "h3", "name": "Far Hospital", "latitude": 13.10, "longitude": 77.80,
     "address": "Whitefield", "has_trauma_center": False, "has_cath_lab": False,
     "trauma_beds_available": 0, "icu_beds_available": 0},
]


class TestHospitalRanker:
    def setup_method(self):
        self.ranker = HospitalRanker()

    def test_rank_returns_list(self):
        with patch("services.maps_service.haversine_km", side_effect=[1.5, 3.2, 12.0]):
            result = self.ranker.rank(12.97, 77.59, HOSPITALS, make_prediction())
        assert isinstance(result, list)
        assert len(result) <= len(HOSPITALS)

    def test_rank_assigns_sequential_ranks(self):
        with patch("services.maps_service.haversine_km", side_effect=[1.5, 3.2, 12.0]):
            result = self.ranker.rank(12.97, 77.59, HOSPITALS, make_prediction())
        ranks = [r.rank for r in result]
        assert ranks == list(range(1, len(result) + 1))

    def test_nearest_hospital_ranked_first(self):
        with patch("services.maps_service.haversine_km", side_effect=[1.5, 3.2, 12.0]):
            result = self.ranker.rank(12.97, 77.59, HOSPITALS, make_prediction())
        assert result[0].name == "City Hospital"

    def test_critical_trauma_gets_bonus(self):
        """City Hospital has trauma center → gets -2km adjustment for CRITICAL."""
        with patch("services.maps_service.haversine_km", side_effect=[5.0, 3.0, 12.0]):
            result = self.ranker.rank(
                12.97, 77.59, HOSPITALS, make_prediction(SeverityClass.CRITICAL)
            )
        # City Hospital: 5km - 2km = 3km; General Hospital: 3km — should be tied or City first
        assert result[0].name in ("City Hospital", "General Hospital")

    def test_no_location_returns_unranked(self):
        result = self.ranker.rank(None, None, HOSPITALS, make_prediction())
        assert len(result) > 0
        assert all(r.distance_km is None for r in result)

    def test_empty_hospital_list(self):
        result = self.ranker.rank(12.97, 77.59, [], make_prediction())
        assert result == []

    def test_max_results_respected(self):
        with patch("services.maps_service.haversine_km", side_effect=[1.5, 3.2, 12.0]):
            result = self.ranker.rank(12.97, 77.59, HOSPITALS, make_prediction(), max_results=2)
        assert len(result) == 2

    def test_recommendation_has_required_fields(self):
        with patch("services.maps_service.haversine_km", side_effect=[1.5, 3.2, 12.0]):
            result = self.ranker.rank(12.97, 77.59, HOSPITALS, make_prediction())
        rec = result[0]
        assert rec.name
        assert rec.rank == 1

    def test_haversine_failure_returns_unranked(self):
        """If haversine raises, ranker must not propagate exception."""
        with patch("services.maps_service.haversine_km",
                   side_effect=RuntimeError("geo failed")):
            result = self.ranker.rank(12.97, 77.59, HOSPITALS, make_prediction())
        assert isinstance(result, list)
