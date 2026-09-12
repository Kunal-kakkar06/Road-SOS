# ai/schemas/__init__.py
from .input_schema import AIInput
from .feature_schema import FeatureVector, TextFeatures, PatientFeatures, AudioFeatures, ImageFeatures, LocationFeatures
from .prediction_schema import SeverityClass, SeverityPrediction
from .decision_schema import EmergencyDecision, UnifiedAIResponse

__all__ = [
    "AIInput",
    "FeatureVector", "TextFeatures", "PatientFeatures",
    "AudioFeatures", "ImageFeatures", "LocationFeatures",
    "SeverityClass", "SeverityPrediction",
    "EmergencyDecision", "UnifiedAIResponse",
]
