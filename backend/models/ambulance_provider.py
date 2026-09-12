from sqlalchemy import Column, String, Boolean, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import os
from database import Base

class AmbulanceProvider(Base):
    __tablename__ = "ambulance_providers"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    name             = Column(String,  nullable=False)
    operator_name    = Column(String,  nullable=True)   # driver name
    phone            = Column(String,  nullable=False)  # driver phone
    vehicle_number   = Column(String,  nullable=True)
    type             = Column(String,  nullable=True)   # basic / als / icu / air

    # Verification
    is_verified      = Column(Boolean, default=False)
    license_number   = Column(String,  nullable=True)
    verified_at      = Column(DateTime, nullable=True)

    # Live location (updated by driver every 5s when active)
    latitude         = Column(Float,   nullable=True)
    longitude        = Column(Float,   nullable=True)
    location_updated = Column(DateTime, nullable=True)

    # Status
    is_available     = Column(Boolean, default=True)
    is_active        = Column(Boolean, default=True)   # on duty

    created_at       = Column(DateTime, server_default=func.now())
