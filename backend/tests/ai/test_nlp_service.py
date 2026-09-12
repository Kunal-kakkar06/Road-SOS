import pytest
from ai.feature_engine.nlp_service import extract_features

def test_minor_headache():
    text = "Minor headache and mild discomfort."
    feat = extract_features(text)
    assert feat.nlp_severity_score == 0.4
    assert feat.moderate_keyword_count == 0
    assert feat.serious_keyword_count == 0
    assert feat.emergency_keyword_count == 0
    assert feat.pain_severity_indicator > 0

def test_deep_cut():
    text = "I have a deep cut on my arm and there is significant bleeding."
    feat = extract_features(text)
    assert feat.bleeding_indicator > 0
    assert feat.trauma_indicator > 0
    assert feat.serious_keyword_count == 1
    assert feat.nlp_severity_score >= 0.7

def test_unconscious():
    text = "I am unconscious and not breathing."
    feat = extract_features(text)
    assert feat.unconsciousness_indicator == 1.0
    assert feat.breathing_difficulty_indicator == 1.0
    assert feat.emergency_keyword_count == 1
    assert feat.nlp_severity_score >= 0.85

def test_vehicle_collision():
    text = "Vehicle collision, person trapped inside vehicle, fire present."
    feat = extract_features(text)
    assert feat.accident_indicator == 1.0
    assert feat.trapped_indicator == 1.0
    assert feat.fire_indicator == 1.0
    assert feat.serious_keyword_count == 1
    assert feat.nlp_severity_score >= 0.7

def test_massive_collision():
    text = "There was a massive collision and someone is trapped in a burning car! Send an ambulance immediately!"
    feat = extract_features(text)
    assert feat.trapped_indicator == 1.0
    assert feat.fire_indicator == 1.0 # "burning" is in fire
    assert feat.urgency_indicator == 1.0
    assert feat.serious_keyword_count == 1
    assert feat.nlp_severity_score >= 0.75

def test_slightly_tired():
    text = "I feel slightly tired but otherwise okay."
    feat = extract_features(text)
    assert feat.nlp_severity_score == 0.4
    assert feat.serious_keyword_count == 0
    assert feat.emergency_keyword_count == 0

def test_negation():
    text = "I am NOT having chest pain."
    feat = extract_features(text)
    # The chest pain indicator should be negated (0)
    assert feat.chest_pain_indicator == 0.0

def test_negation_bleeding():
    text = "There is no bleeding."
    feat = extract_features(text)
    assert feat.bleeding_indicator == 0.0
