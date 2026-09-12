from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from database import Base

class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    worker_id      = Column(String, primary_key=True)         # worker-uuid string
    status         = Column(String, default="active", index=True) # active, stopping, dead
    current_job_id = Column(String, nullable=True)
    completed_jobs = Column(Integer, default=0)
    failed_jobs    = Column(Integer, default=0)
    started_at     = Column(DateTime, server_default=func.now())
    last_heartbeat = Column(DateTime, server_default=func.now(), onupdate=func.now())
