from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, Integer
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from database import Base


class TriageJob(Base):
    __tablename__ = "triage_jobs"
    
    id         = Column(String, primary_key=True)          # UUID string
    user_id    = Column(String, index=True, nullable=False)
    status     = Column(String, default="pending", index=True) # pending, processing, completed, failed
    request_id = Column(String, nullable=True, index=True)
    payload    = Column(JSON, nullable=True)               # Stores the TriageRequest
    result     = Column(JSON, nullable=True)
    error      = Column(String, nullable=True)
    
    # Worker Tracking
    worker_id     = Column(String, nullable=True, index=True)
    attempt_count = Column(Integer, default=0)
    started_at    = Column(DateTime, nullable=True)
    heartbeat_at  = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

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
    
    # Audit & Observability Metadata (Step 7)
    job_id                 = Column(String, nullable=True, index=True)
    processing_mode        = Column(String, nullable=True, default="sync") # sync, async
    status                 = Column(String, nullable=True, default="completed") # completed, failed
    processing_duration_ms = Column(Integer, nullable=True)
    model_version          = Column(String, nullable=True)
    feature_version        = Column(String, nullable=True)
    model_type             = Column(String, nullable=True)
    error_message          = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
