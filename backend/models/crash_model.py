from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import os
from database import Base

class CrashEvent(Base):
    __tablename__ = "crash_events"

    if "sqlite" in os.getenv("DATABASE_URL", ""):
        id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    else:
        id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id          = Column(String,  unique=True, nullable=False, index=True)
    user_id           = Column(String,  nullable=False)
    latitude          = Column(Float)
    longitude         = Column(Float)
    timestamp         = Column(String,  nullable=False)
    crash_probability = Column(Float,   nullable=False)
    severity          = Column(String,  nullable=False)
    severity_label    = Column(String)
    sensor_data       = Column(JSON)
    was_manual        = Column(Boolean, default=False)
    sos_triggered     = Column(Boolean, default=False)
    cancelled         = Column(Boolean, default=False)
    created_at        = Column(DateTime, server_default=func.now())
