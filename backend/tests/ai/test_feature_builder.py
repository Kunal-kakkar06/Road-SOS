"""
tests/ai/test_feature_builder.py
Tests for FeatureBuilder — mocks at the services.nlp_triage level since
the feature extractors import functions locally inside methods.
"""
from unittest.mock import patch, MagicMock
from ai.feature_engine.feature_builder import FeatureBuilder
from ai.schemas.input_schema import AIInput


def make_input(**kwargs) -> AIInput:
    return AIInput(**kwargs)


def test_builder_returns_feature_vector():
    builder = FeatureBuilder()
    ai = make_input(symptoms="chest pain", age=45)
    with patch("services.nlp_triage.extract_severity_from_text",
               return_value={"score": 0.8, "keywords_hit": 2}):
        fv = builder.build(ai)
    assert fv is not None
    assert fv.signal_count >= 0


def test_builder_text_only():
    builder = FeatureBuilder()
    ai = make_input(symptoms="dizziness and nausea")
    with patch("services.nlp_triage.extract_severity_from_text",
               return_value={"score": 0.5, "keywords_hit": 1}):
        fv = builder.build(ai)
    assert fv.text.raw_text_available is True
    assert fv.audio.audio_available is False
    assert fv.image.image_available is False


def test_builder_with_pre_computed_scores():
    """When nlp_score and image_score are pre-computed, no service call needed."""
    builder = FeatureBuilder()
    ai = make_input(
        symptoms="chest pain",
        has_voice=True,
        has_image=True,
        nlp_score=0.75,
        image_score=0.9,
        voice_transcript="I feel dizzy",
    )
    fv = builder.build(ai)
    assert fv.audio.audio_available is True
    assert fv.audio.nlp_severity_score == 0.75
    assert fv.image.image_available is True
    assert fv.image.image_severity_score == 0.9


def test_builder_signal_count():
    builder = FeatureBuilder()
    ai = make_input(
        symptoms="pain",
        has_voice=True,
        nlp_score=0.6,
        voice_transcript="pain",
    )
    with patch("services.nlp_triage.extract_severity_from_text",
               return_value={"score": 0.5, "keywords_hit": 0}):
        fv = builder.build(ai)
    # text + audio = 2
    assert fv.signal_count == 2


def test_builder_with_location():
    builder = FeatureBuilder()
    ai = make_input(latitude=12.97, longitude=77.59)
    with patch("services.nlp_triage.extract_severity_from_text",
               return_value={"score": 0.3, "keywords_hit": 0}):
        fv = builder.build(ai)
    assert fv.location.has_location is True
    assert fv.location.latitude == 12.97


def test_builder_extractor_failure_is_isolated():
    """If one extractor fails, others must still succeed."""
    builder = FeatureBuilder()
    ai = make_input(symptoms="severe bleeding", has_image=True, image_score=0.85)
    with patch("services.nlp_triage.extract_severity_from_text",
               side_effect=RuntimeError("NLP crashed")):
        fv = builder.build(ai)
    # Text feature extraction failed but image should still work
    assert fv.image.image_available is True


def test_builder_with_medical_profile():
    builder = FeatureBuilder()
    ai = make_input(
        symptoms="chest pain",
        age=55,
        medical_profile={
            "conditions": ["Hypertension", "Diabetes"],
            "medications": ["Metformin", "Lisinopril"],
            "allergies": ["Penicillin"],
        },
    )
    with patch("services.nlp_triage.extract_severity_from_text",
               return_value={"score": 0.7, "keywords_hit": 1}):
        fv = builder.build(ai)
    assert fv.patient.medical_risk_score is not None
    assert fv.patient.medical_risk_score > 0.3
    assert fv.patient.has_diabetes is True
    assert fv.patient.has_hypertension is True
