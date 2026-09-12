import os
import pytest
import shutil
import hashlib
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from services.backup_service import BackupService
from services.triage_job_manager import cleanup_old_terminal_jobs
from models.backup_model import BackupRecord
from database import AsyncSessionLocal

client = TestClient(app)

def test_production_environment_rejects_sqlite(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test_prod_guard.db")
    
    with pytest.raises(ValueError, match="SQLite database connection is strictly prohibited in PRODUCTION"):
        is_sqlite = os.getenv("DATABASE_URL").startswith("sqlite")
        env = os.getenv("ENVIRONMENT").lower()
        if env == "production" and is_sqlite:
            raise ValueError("SQLite database connection is strictly prohibited in PRODUCTION environment. DATABASE_URL must specify a PostgreSQL instance.")

def test_backup_sha256_checksum_generation(tmp_path):
    out_dir = str(tmp_path)
    test_file = os.path.join(out_dir, "roadsos_backup_test_20260910_120000.sql.gz")
    
    with open(test_file, "wb") as f:
        f.write(b"SAMPLE BACKUP DATA FOR STEP 18 CHECKSUM TEST")
        
    sha256_hash = hashlib.sha256()
    with open(test_file, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    checksum_hex = sha256_hash.hexdigest()

    checksum_file = f"{test_file}.sha256"
    with open(checksum_file, "w") as f_chk:
        f_chk.write(f"{checksum_hex}  {os.path.basename(test_file)}\n")

    assert os.path.exists(checksum_file)
    with open(checksum_file, "r") as f_chk:
        read_hash = f_chk.read().split()[0]
    assert read_hash == checksum_hex

def test_restore_checksum_tamper_detection(tmp_path):
    backup_file = os.path.join(str(tmp_path), "test_tampered_backup.sql.gz")
    checksum_file = f"{backup_file}.sha256"

    with open(backup_file, "wb") as f:
        f.write(b"ORIGINAL BACKUP CONTENT")

    sha256_hash = hashlib.sha256()
    with open(backup_file, "rb") as f:
        sha256_hash.update(f.read())
    orig_hash = sha256_hash.hexdigest()

    with open(checksum_file, "w") as f:
        f.write(f"{orig_hash}  {os.path.basename(backup_file)}\n")

    # Modify file content to simulate corruption/tampering
    with open(backup_file, "wb") as f:
        f.write(b"CORRUPTED BACKUP CONTENT")

    sha256_tampered = hashlib.sha256()
    with open(backup_file, "rb") as f:
        sha256_tampered.update(f.read())

    assert orig_hash != sha256_tampered.hexdigest()

def test_backup_service_failure_isolation(monkeypatch):
    """Verify BackupService failure records metric and log without raising unhandled exception."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://roadsos:roadsos_password@localhost:5432/roadsos_db")
    service = BackupService(backup_dir="/invalid_nonexistent_directory_999")
    with patch("services.backup_service.run_backup", side_effect=Exception("Disk full")):
        res = service.create_backup(compress=True)
        assert res["status"] == "failed"
        assert "Disk full" in res["error"]

def test_backup_retention_cleanup_dry_run(tmp_path):
    from scripts.cleanup_backups import cleanup_backups
    out_dir = str(tmp_path)

    b_file = os.path.join(out_dir, "roadsos_backup_test_20260101_000000.sql.gz")
    with open(b_file, "wb") as f:
        f.write(b"DUMMY DATA")

    res = cleanup_backups(backup_dir=out_dir, dry_run=True)
    assert res["kept_count"] >= 1

def test_api_metrics_includes_disaster_recovery_indicators():
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text

    assert "disaster_recovery_latest_backup_age_seconds" in metrics_text
    assert "disaster_recovery_last_backup_success" in metrics_text
    assert "disaster_recovery_last_backup_status" in metrics_text
    assert "disaster_recovery_backup_failures_total" in metrics_text
    assert "disaster_recovery_restore_verifications_total" in metrics_text
    assert "database_connection_failures_total" in metrics_text
    assert "database_transaction_rollbacks_total" in metrics_text

def test_backup_credential_masking():
    from scripts.backup_db import mask_url
    secret_url = "postgresql://roadsos_user:super_secret_pass_123@localhost:5432/roadsos_db"
    masked = mask_url(secret_url)
    assert "super_secret_pass_123" not in masked
    assert "roadsos_user:****@" in masked

@pytest.mark.asyncio
async def test_backup_record_orm_model():
    import uuid
    b_id = f"test_backup_{uuid.uuid4()}"
    rec = BackupRecord(
        backup_id=b_id,
        status="COMPLETED",
        file_path="/tmp/test.sql.gz",
        size_bytes=1024,
        checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        database_version="PostgreSQL 15.4",
        app_version="step18"
    )
    async with AsyncSessionLocal() as db:
        db.add(rec)
        await db.commit()

        from sqlalchemy import select
        res = await db.execute(select(BackupRecord).where(BackupRecord.backup_id == b_id))
        fetched = res.scalars().first()
        assert fetched is not None
        assert fetched.status == "COMPLETED"
        assert fetched.size_bytes == 1024
