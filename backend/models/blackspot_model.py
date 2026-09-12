import os
from sqlalchemy import Column, String, Float, Integer, DateTime
from sqlalchemy.sql import func
import uuid as uuid_mod
from database import Base

class AccidentBlackspot(Base):
    __tablename__ = "accident_blackspots"
    
    id            = Column(String, primary_key=True, default=lambda: str(uuid_mod.uuid4()))
    latitude      = Column(Float,  nullable=False)
    longitude     = Column(Float,  nullable=False)
    total_accidents = Column(Integer, default=0)
    fatal_accidents = Column(Integer, default=0)
    road_name     = Column(String, nullable=True)
    area_name     = Column(String, nullable=True)
    risk_level    = Column(String, default="medium")  # low/medium/high/critical
    primary_cause = Column(String, nullable=True)
    intensity     = Column(Float,  default=0.5)       # 0.0–1.0 heatmap weight
    year          = Column(Integer, nullable=True)
    created_at    = Column(DateTime, server_default=func.now())

    # Latitude & Longitude standard columns used for cross-database compatibility
