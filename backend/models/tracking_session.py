from sqlalchemy import Column, String, Float, Boolean, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid as uuid_mod
from database import Base


class TrackingSession(Base):
    """
    One session per SOS event.
    Family opens /track/{session_id} to see live location.
    Session expires after 24 hours or when manually closed.
    """
    __tablename__ = "tracking_sessions"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    session_id      = Column(String, unique=True, nullable=False, index=True)
    sos_event_id    = Column(String, nullable=True)
    incident_id     = Column(String, nullable=True)
    user_id         = Column(String, nullable=False)

    # Patient info snapshot (for family tracking page)
    patient_name    = Column(String, nullable=True)
    severity        = Column(String, nullable=True)     # P1/P2/P3/P4
    hospital_name   = Column(String, nullable=True)
    ambulance_name  = Column(String, nullable=True)

    # Location
    initial_lat     = Column(Float,  nullable=True)
    initial_lng     = Column(Float,  nullable=True)
    latest_lat      = Column(Float,  nullable=True)
    latest_lng      = Column(Float,  nullable=True)
    location_updated= Column(DateTime, nullable=True)

    # Contacts notified
    contacts_notified = Column(JSON, default=list)
    # [{"name":"Sarah K","phone":"+919876543210","sms_sent":true}]

    # Status
    is_active       = Column(Boolean, default=True)
    sms_sent        = Column(Boolean, default=False)
    was_offline     = Column(Boolean, default=False)  # SMS sent offline

    created_at      = Column(DateTime, server_default=func.now())
    expires_at      = Column(DateTime, nullable=True)  # 24h from creation
