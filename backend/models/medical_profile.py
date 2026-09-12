from sqlalchemy import Column, String, Boolean, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from database import Base


class MedicalProfile(Base):
    __tablename__ = "medical_profiles"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id         = Column(String, unique=True, nullable=False, index=True)

    # Personal
    full_name       = Column(String,  nullable=False)
    date_of_birth   = Column(String,  nullable=True)   # DD/MM/YYYY
    gender          = Column(String,  nullable=True)
    phone           = Column(String,  nullable=True)
    photo_url       = Column(String,  nullable=True)

    # Critical medical
    blood_type      = Column(String,  nullable=True)   # A+, B-, O+, etc.
    allergies       = Column(JSON,    default=list)     # ["Penicillin", "Aspirin"]
    medications     = Column(JSON,    default=list)     # ["Metformin 500mg"]
    conditions      = Column(JSON,    default=list)     # ["Hypertension", "Diabetes"]
    disabilities    = Column(JSON,    default=list)     # ["Hearing impaired"]

    # Emergency contacts
    emergency_contacts = Column(JSON, default=list)
    # [{"name":"Sarah K","phone":"+919876543210","relation":"Wife"}]

    # Insurance
    insurance_provider  = Column(String, nullable=True)
    insurance_policy_no = Column(String, nullable=True)

    # Source flags
    digilocker_linked   = Column(Boolean, default=False)
    abha_id             = Column(String,  nullable=True)  # ABHA number

    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())
