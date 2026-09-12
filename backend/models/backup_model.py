from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class BackupRecord(Base):
    __tablename__ = "backup_records"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    backup_id        = Column(String(255), unique=True, index=True, nullable=False)
    created_at       = Column(DateTime, server_default=func.now(), nullable=False)
    completed_at     = Column(DateTime, nullable=True)
    status           = Column(String(50), nullable=False, default="RUNNING")  # RUNNING, COMPLETED, FAILED, VERIFIED
    file_path        = Column(String(500), nullable=True)
    size_bytes       = Column(Integer, nullable=True)
    checksum         = Column(String(128), nullable=True)
    database_version = Column(String(100), nullable=True)
    app_version      = Column(String(50), nullable=True)
    error_message    = Column(Text, nullable=True)
