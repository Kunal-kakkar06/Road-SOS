from sqlalchemy import Column, String, Boolean, Float, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import os
from database import Base

class DispatchEvent(Base):
    __tablename__ = "dispatch_events"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    dispatch_id       = Column(String, unique=True, nullable=False, index=True)
    sos_event_id      = Column(String, nullable=True)   # links to sos_events table
    provider_id       = Column(String, nullable=False)

    # Patient location
    patient_lat       = Column(Float, nullable=False)
    patient_lng       = Column(Float, nullable=False)
    patient_user_id   = Column(String, nullable=True)

    # Dispatch details
    eta_minutes       = Column(Float, nullable=True)
    distance_km       = Column(Float, nullable=True)
    route_url         = Column(Text,  nullable=True)
    driver_sms_sent   = Column(Boolean, default=False)

    # Status
    status = Column(String, default="dispatched")
    # dispatched → en_route → arrived → completed / cancelled

    dispatched_at     = Column(DateTime, server_default=func.now())
    arrived_at        = Column(DateTime, nullable=True)
    completed_at      = Column(DateTime, nullable=True)
