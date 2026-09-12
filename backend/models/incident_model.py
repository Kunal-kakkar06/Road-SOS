from sqlalchemy import Column, String, Float, DateTime, JSON, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id     = Column(String, unique=True, nullable=False, index=True)
    user_id         = Column(String, nullable=False, index=True)

    # Links to other features
    sos_event_id    = Column(String, nullable=True)
    crash_event_id  = Column(String, nullable=True)
    dispatch_id     = Column(String, nullable=True)

    # Crash location
    latitude        = Column(Float,  nullable=True)
    longitude       = Column(Float,  nullable=True)
    address         = Column(Text,   nullable=True)

    # Crash details
    severity        = Column(String, nullable=True)   # P1/P2/P3/P4
    crash_timestamp = Column(DateTime, nullable=True)
    speed_at_impact = Column(Float,  nullable=True)

    # Response
    medical_profile = Column(JSON,   nullable=True)
    hospital_name   = Column(String, nullable=True)
    ambulance_name  = Column(String, nullable=True)

    # Evidence
    photo_urls      = Column(JSON, default=list)
    pdf_url         = Column(String, nullable=True)

    # Status
    status          = Column(String, default="open")
    fir_state       = Column(String, nullable=True, default="Karnataka")

    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=False, index=True)
    event_type  = Column(String, nullable=False)
    # crash_detected | sos_triggered | ambulance_dispatched |
    # ambulance_arrived | hospital_admitted | report_generated
    description = Column(Text,   nullable=True)
    event_metadata = Column(JSON,   nullable=True)
    timestamp   = Column(DateTime, server_default=func.now())


class FIRTemplate(Base):
    __tablename__ = "fir_templates"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    state      = Column(String, unique=True, nullable=False, index=True)
    steps      = Column(JSON,   nullable=False)
    updated_at = Column(DateTime, server_default=func.now())
