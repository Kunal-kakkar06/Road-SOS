"""
tests/ai/test_input_schema.py
Tests for AIInput validation and optional field handling.
"""
import pytest
from ai.schemas.input_schema import AIInput


def test_default_request_id_is_generated():
    ai = AIInput()
    assert ai.request_id, "request_id must be auto-generated"
    assert len(ai.request_id) == 36  # UUID4 format


def test_all_fields_optional():
    """AIInput must be constructible with zero arguments."""
    ai = AIInput()
    assert ai.symptoms is None
    assert ai.age is None
    assert ai.gender is None
    assert ai.latitude is None
    assert ai.longitude is None


def test_explicit_request_id():
    ai = AIInput(request_id="custom-id-123")
    assert ai.request_id == "custom-id-123"


def test_pain_level_clamped():
    ai = AIInput(pain_level=15)
    assert ai.pain_level == 10

    ai2 = AIInput(pain_level=-5)
    assert ai2.pain_level == 1


def test_valid_pain_level():
    ai = AIInput(pain_level=7)
    assert ai.pain_level == 7


def test_has_voice_defaults_false():
    ai = AIInput()
    assert ai.has_voice is False
    assert ai.has_image is False
    assert ai.has_sensor_data is False


def test_signal_flags_settable():
    ai = AIInput(has_voice=True, has_image=True, nlp_score=0.75, image_score=0.9)
    assert ai.has_voice is True
    assert ai.has_image is True
    assert ai.nlp_score == 0.75
    assert ai.image_score == 0.9


def test_extra_fields_ignored():
    """Extra fields must not cause validation errors."""
    ai = AIInput(**{"symptoms": "chest pain", "unknown_future_field": "value"})
    assert ai.symptoms == "chest pain"


def test_latitude_longitude_bounds():
    with pytest.raises(Exception):
        AIInput(latitude=200.0)  # out of range

    with pytest.raises(Exception):
        AIInput(longitude=-200.0)


def test_medical_profile_optional():
    ai = AIInput(medical_profile={"blood_type": "O+", "allergies": ["Penicillin"]})
    assert ai.medical_profile["blood_type"] == "O+"
