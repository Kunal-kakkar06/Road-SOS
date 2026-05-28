from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import os
from database import Base

class SOSEvent(Base):
    __tablename__ = "sos_events"

    if "sqlite" in os.getenv("DATABASE_URL", ""):
        id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    else:
        id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    event_id        = Column(String,  unique=True, nullable=False, index=True)
    user_id         = Column(String,  nullable=False, index=True)
    latitude        = Column(Float,   nullable=False)
    longitude       = Column(Float,   nullable=False)
    timestamp       = Column(String,  nullable=False)
    medical_profile = Column(JSON,    nullable=True)
    contacts        = Column(JSON,    nullable=True)
    sms_sent        = Column(Boolean, default=False)
    sms_count       = Column(Integer, default=0)
    was_offline     = Column(Boolean, default=False)
    synced_at       = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, server_default=func.now())
