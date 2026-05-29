from sqlalchemy import Column, String, Float, Boolean, DateTime, Text
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from database import Base


class TriageEvent(Base):
    __tablename__ = "triage_events"

    id            = Column(String, primary_key=True)          # UUID string
    event_id      = Column(String, unique=True, nullable=False, index=True)
    incident_id   = Column(String, nullable=True)
    user_id       = Column(String, nullable=True)

    # Input signal flags
    has_image       = Column(Boolean, default=False)
    has_voice       = Column(Boolean, default=False)
    has_sensor_data = Column(Boolean, default=False)
    transcript      = Column(Text, nullable=True)            # Whisper output

    # Individual model scores (0.0–1.0)
    image_score   = Column(Float, nullable=True)
    nlp_score     = Column(Float, nullable=True)
    sensor_score  = Column(Float, nullable=True)

    # Fusion result
    final_severity  = Column(String, nullable=True)          # P1/P2/P3/P4
    final_score     = Column(Float,  nullable=True)          # 0.0–1.0 confidence
    severity_label  = Column(String, nullable=True)
    shap_factors    = Column(JSON,   nullable=True)          # top-3 SHAP dicts
    was_offline     = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
