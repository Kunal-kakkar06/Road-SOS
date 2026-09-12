"""
Re-export all model classes from models.py at the package root.
This resolves the conflict between models.py and models/ directory.
"""
import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    licence_number = Column(String(100), nullable=False)
    licence_expiry = Column(Date, nullable=False)
    is_verified = Column(Boolean, default=False)
    contact_phone = Column(String(20), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    ambulances = relationship("Ambulance", back_populates="provider", cascade="all, delete-orphan")


class Ambulance(Base):
    __tablename__ = "ambulances"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    vehicle_number = Column(String(50), nullable=False)
    driver_name = Column(String(100), nullable=False)
    driver_phone = Column(String(20), nullable=False)
    is_available = Column(Boolean, default=True)
    current_lat = Column(Float, nullable=False)
    current_lng = Column(Float, nullable=False)
    last_ping = Column(DateTime, server_default=func.now(), onupdate=func.now())

    provider = relationship("Provider", back_populates="ambulances")
    dispatches = relationship("DispatchRequest", back_populates="assigned_ambulance")


class DispatchRequest(Base):
    __tablename__ = "dispatch_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_lat = Column(Float, nullable=False)
    incident_lng = Column(Float, nullable=False)
    incident_address = Column(String(500), nullable=False)
    assigned_ambulance_id = Column(Integer, ForeignKey("ambulances.id"), nullable=True)
    status = Column(String(50), default="pending")
    patient_name = Column(String(100), nullable=False)
    patient_phone = Column(String(20), nullable=False)
    severity = Column(Integer, nullable=False)
    requested_at = Column(DateTime, server_default=func.now())
    assigned_at = Column(DateTime, nullable=True)
    arrived_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    assigned_ambulance = relationship("Ambulance", back_populates="dispatches")
    audit_logs = relationship("AuditLog", back_populates="dispatch_request", cascade="all, delete-orphan")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("dispatch_requests.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    dispatch_request = relationship("DispatchRequest", back_populates="audit_logs")


# Also import MedicalProfile from submodule
try:
    from .medical_profile import MedicalProfile
except ImportError:
    pass

try:
    from .hospital_model import Hospital
except ImportError:
    pass

try:
    from .incident_model import Incident, IncidentEvent, FIRTemplate
except ImportError:
    pass

try:
    from .tracking_session import TrackingSession
except ImportError:
    pass

try:
    from .sos_model import SOSEvent
except ImportError:
    pass

try:
    from .crash_model import CrashEvent
except ImportError:
    pass

try:
    from .ambulance_provider import AmbulanceProvider
except ImportError:
    pass

try:
    from .dispatch_event import DispatchEvent
except ImportError:
    pass

try:
    from .user import User, RefreshToken, ResponderAssignment
except ImportError:
    pass

try:
    from .triage_model import TriageEvent, TriageJob
except ImportError:
    pass

try:
    from .worker_model import WorkerHeartbeat
except ImportError:
    pass

try:
    from .backup_model import BackupRecord
except ImportError:
    pass

try:
    from .backup_replica import BackupReplica
except ImportError:
    pass




