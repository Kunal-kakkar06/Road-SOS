"""
ai/decision/hospital_ranker.py
================================
Clean interface for ranking hospitals by relevance to a specific emergency.

Current implementation: distance-based ranking using existing
services.maps_service.haversine_km.

Future implementation: weighted scoring combining distance + capability
match + bed availability + travel time — all without LLM involvement.

The ranking algorithm can be upgraded by editing _score_hospital()
without changing the public API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ai.schemas.decision_schema import HospitalRecommendation
from ai.schemas.prediction_schema import SeverityClass, SeverityPrediction

logger = logging.getLogger("roadsos.ai.decision.hospital_ranker")


class HospitalRanker:
    """
    Ranks available hospitals for a given location and severity.

    Accepts:
      - user latitude / longitude
      - list of hospital dicts (from DB or Overpass API)
      - severity prediction (to weight capability requirements)

    Returns:
      - Ordered list of HospitalRecommendation
    """

    def rank(
        self,
        user_lat: Optional[float],
        user_lng: Optional[float],
        hospitals: List[Dict[str, Any]],
        prediction: Optional[SeverityPrediction] = None,
        max_results: int = 5,
    ) -> List[HospitalRecommendation]:
        """
        Rank hospitals and return up to max_results recommendations.

        If user location is unavailable, returns hospitals in their
        original order (unranked) with a flag.

        Never raises — returns an empty list on unexpected failure.
        """
        if not hospitals:
            return []

        if user_lat is None or user_lng is None:
            logger.info("[HospitalRanker] No user location — returning unranked list.")
            return self._unranked(hospitals, max_results)

        try:
            scored = [
                self._score_hospital(h, user_lat, user_lng, prediction)
                for h in hospitals
            ]
            scored.sort(key=lambda x: x[0])  # ascending score = better rank

            recommendations = []
            for rank_idx, (_, hospital, rec) in enumerate(scored[:max_results], start=1):
                rec.rank = rank_idx
                recommendations.append(rec)

            return recommendations

        except Exception as exc:
            logger.error("[HospitalRanker] ranking failed: %s", exc)
            return self._unranked(hospitals, max_results)

    # ── Internals ─────────────────────────────────────────────

    def _score_hospital(
        self,
        hospital: Dict[str, Any],
        user_lat: float,
        user_lng: float,
        prediction: Optional[SeverityPrediction],
    ):
        """
        Compute a ranking score for a single hospital.

        Lower score = better rank.  Currently pure distance (km).
        Future: composite of distance + capability + bed availability.
        """
        h_lat = hospital.get("latitude") or hospital.get("lat")
        h_lng = hospital.get("longitude") or hospital.get("lng")

        distance_km: Optional[float] = None
        if h_lat is not None and h_lng is not None:
            try:
                from services.maps_service import haversine_km
                distance_km = haversine_km(user_lat, user_lng, float(h_lat), float(h_lng))
            except Exception as exc:
                logger.debug("[HospitalRanker] haversine failed: %s", exc)

        # ── Capability match bonus (future scoring hook) ──────
        # When severity is CRITICAL, prefer hospitals with trauma centers.
        # Currently a placeholder — subtract 2 km equivalent for trauma match.
        capability_adjustment = 0.0
        if prediction and prediction.severity_class == SeverityClass.CRITICAL:
            if hospital.get("has_trauma_center"):
                capability_adjustment = -2.0

        score = (distance_km or 999.0) + capability_adjustment

        rec = HospitalRecommendation(
            rank=0,  # set by caller
            hospital_id=str(hospital.get("id", "")),
            name=hospital.get("name", "Unknown Hospital"),
            address=hospital.get("address"),
            distance_km=round(distance_km, 2) if distance_km is not None else None,
            estimated_travel_minutes=None,  # populated by maps_service in future
            has_trauma_center=hospital.get("has_trauma_center"),
            has_cath_lab=hospital.get("has_cath_lab"),
            trauma_beds_available=hospital.get("trauma_beds_available"),
            icu_beds_available=hospital.get("icu_beds_available"),
            ranking_score=round(score, 3),
        )
        return score, hospital, rec

    def _unranked(
        self, hospitals: List[Dict[str, Any]], max_results: int
    ) -> List[HospitalRecommendation]:
        """Return hospitals in original order, rank by list index."""
        result = []
        for idx, h in enumerate(hospitals[:max_results], start=1):
            result.append(
                HospitalRecommendation(
                    rank=idx,
                    hospital_id=str(h.get("id", "")),
                    name=h.get("name", "Unknown Hospital"),
                    address=h.get("address"),
                    distance_km=None,
                    estimated_travel_minutes=None,
                    has_trauma_center=h.get("has_trauma_center"),
                    has_cath_lab=h.get("has_cath_lab"),
                    trauma_beds_available=h.get("trauma_beds_available"),
                    icu_beds_available=h.get("icu_beds_available"),
                    ranking_score=None,
                )
            )
        return result
