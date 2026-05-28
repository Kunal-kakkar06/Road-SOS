from sqlalchemy import Column, String, Integer, Boolean, Float, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
from sqlalchemy.sql import func
import uuid
from database import Base


class Hospital(Base):
    __tablename__ = "hospitals"

    import os
    if "sqlite" in os.getenv("DATABASE_URL", ""):
        id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    else:
        id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name            = Column(String,  nullable=False, index=True)
    address         = Column(Text,    nullable=False)
    phone           = Column(String,  nullable=True)
    type            = Column(String,  nullable=True)   # govt / private / trust

    # Geo — PostGIS point (lng, lat)
    import os
    if "sqlite" in os.getenv("DATABASE_URL", ""):
        location        = Column(Text, nullable=True)
    else:
        location        = Column(Geometry('POINT', srid=4326, spatial_index=False), nullable=True)
    latitude        = Column(Float,   nullable=False)
    longitude       = Column(Float,   nullable=False)

    # Bed availability (updated periodically)
    trauma_beds_total    = Column(Integer, default=0)
    trauma_beds_available= Column(Integer, default=0)
    icu_beds_total       = Column(Integer, default=0)
    icu_beds_available   = Column(Integer, default=0)
    general_beds_available= Column(Integer, default=0)

    # Blood bank
    blood_bank      = Column(Boolean, default=False)
    blood_types_available = Column(JSON, default=list)
    # e.g. ["A+", "B+", "O+", "AB+"]

    # Capabilities
    has_trauma_center = Column(Boolean, default=False)
    has_cath_lab      = Column(Boolean, default=False)   # cardiac
    has_neuro_unit    = Column(Boolean, default=False)

    is_active       = Column(Boolean, default=True)
    beds_updated_at = Column(DateTime, server_default=func.now())
    created_at      = Column(DateTime, server_default=func.now())
