"""
tests/ai/test_feature_schema.py
Tests for FeatureVector and sub-schema construction and summary_dict.
"""
from ai.schemas.feature_schema import (
    AudioFeatures, FeatureVector, ImageFeatures,
    LocationFeatures, PatientFeatures, TextFeatures,
)


def test_feature_vector_defaults_all_none():
    fv = FeatureVector()
    assert fv.text.raw_text_available is False
    assert fv.audio.audio_available is False
    assert fv.image.image_available is False
    assert fv.location.has_location is False
    assert fv.sensor_available is False
    assert fv.signal_count == 0


def test_feature_vector_with_text():
    text = TextFeatures(raw_text_available=True, nlp_severity_score=0.7, symptom_count=3)
    fv = FeatureVector(text=text, signal_count=1)
    assert fv.text.raw_text_available is True
    assert fv.text.nlp_severity_score == 0.7


def test_feature_vector_summary_dict_keys():
    fv = FeatureVector()
    summary = fv.summary_dict()
    required_keys = {
        "has_text", "has_audio", "has_image", "has_sensor",
        "signal_count", "nlp_score", "image_score", "sensor_score", "medical_risk",
    }
    assert required_keys.issubset(set(summary.keys()))


def test_patient_features_all_optional():
    pf = PatientFeatures()
    assert pf.age is None
    assert pf.medical_risk_score is None
    assert pf.has_diabetes is None


def test_audio_features_available():
    af = AudioFeatures(audio_available=True, nlp_severity_score=0.85, transcript="chest pain")
    assert af.audio_available is True
    assert af.nlp_severity_score == 0.85


def test_image_features_available():
    img = ImageFeatures(
        image_available=True,
        image_severity_score=0.9,
        image_confidence="high",
    )
    assert img.image_available is True
    assert img.image_confidence == "high"


def test_location_features():
    loc = LocationFeatures(latitude=12.97, longitude=77.59, has_location=True)
    assert loc.has_location is True
    assert loc.distance_to_nearest_hospital_km is None  # not yet populated


def test_signal_count_reflects_available():
    fv = FeatureVector(
        text=TextFeatures(raw_text_available=True),
        audio=AudioFeatures(audio_available=True),
        image=ImageFeatures(image_available=False),
        sensor_available=False,
        signal_count=2,
    )
    assert fv.signal_count == 2
