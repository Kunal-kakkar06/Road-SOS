from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from database import Base

class BackupReplica(Base):
    __tablename__ = "backup_replicas"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    backup_id           = Column(String(255), ForeignKey("backup_records.backup_id"), nullable=False, index=True)
    storage_provider    = Column(String(50), nullable=False, default="s3")
    bucket              = Column(String(255), nullable=False)
    object_key          = Column(String(500), nullable=False, index=True)
    region              = Column(String(50), nullable=True)
    encryption_mode     = Column(String(50), nullable=True, default="AES256")
    encryption_key_id   = Column(String(255), nullable=True)
    remote_etag         = Column(String(128), nullable=True)
    remote_sha256       = Column(String(128), nullable=True)
    remote_size_bytes   = Column(Integer, nullable=True)
    upload_started_at   = Column(DateTime, server_default=func.now(), nullable=True)
    uploaded_at         = Column(DateTime, nullable=True)
    verified_at         = Column(DateTime, nullable=True)
    restore_verified_at = Column(DateTime, nullable=True)
    status              = Column(String(50), nullable=False, default="RUNNING")  # RUNNING, COMPLETED, VERIFIED, FAILED
    attempt_count       = Column(Integer, default=1)
    last_error          = Column(Text, nullable=True)
    created_at          = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at          = Column(DateTime, server_default=func.now(), onupdate=func.now())
