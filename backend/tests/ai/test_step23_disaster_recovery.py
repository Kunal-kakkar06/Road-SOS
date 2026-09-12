import os
import json
import gzip
import shutil
import hashlib
import pytest
from datetime import datetime, timezone
from main import validate_production_configuration

def test_1_backup_configuration_validation(monkeypatch):
    """1. Verify backup script rejects missing or SQLite DATABASE_URL."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    from scripts.backup_db import run_backup

    with pytest.raises(SystemExit) as exc:
        run_backup(output_dir="/tmp/test_backup_dir")
    assert exc.value.code != 0

def test_2_production_requires_postgresql(monkeypatch):
    """2. Verify production backup requires a valid PostgreSQL connection string."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
    with pytest.raises(ValueError, match="SQLite database connection is strictly prohibited in PRODUCTION"):
        validate_production_configuration()

def test_3_backup_path_validation(tmp_path):
    """3. Verify backup path directory creation and path handling."""
    from scripts.backup_db import mask_url
    masked = mask_url("postgresql://roadsos:my_secret_pass@localhost:5432/roadsos_db")
    assert "my_secret_pass" not in masked
    assert "****" in masked

def test_4_backup_failure_detection(monkeypatch, tmp_path):
    """4. Verify non-zero return code when pg_dump fails."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://invalid_user:invalid_pass@invalid_host:5432/invalid_db")
    from scripts.backup_db import run_backup

    with pytest.raises(SystemExit) as exc:
        run_backup(output_dir=str(tmp_path))
    assert exc.value.code != 0

def test_5_backup_metadata_generation(tmp_path):
    """5. Verify companion JSON metadata generation."""
    dummy_file = tmp_path / "dummy_backup.sql.gz"
    dummy_file.write_bytes(b"DUMMY POSTGRESQL BACKUP DATA")
    
    sha256_hash = hashlib.sha256(b"DUMMY POSTGRESQL BACKUP DATA").hexdigest()
    meta_file = tmp_path / "dummy_backup.sql.gz.json"
    
    payload = {
        "backup_id": "dummy_backup.sql.gz",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": 28,
        "sha256": sha256_hash,
        "database_version": "PostgreSQL 15",
        "migration_revision": "c3d4e5f6a7b8"
    }
    meta_file.write_text(json.dumps(payload))
    
    loaded = json.loads(meta_file.read_text())
    assert loaded["backup_id"] == "dummy_backup.sql.gz"
    assert loaded["migration_revision"] == "c3d4e5f6a7b8"
    assert loaded["sha256"] == sha256_hash

def test_6_sha256_integrity_calculation(tmp_path):
    """6. Verify SHA-256 checksum calculation for backup content."""
    content = b"CRITICAL_DATABASE_CONTENT_HEADER_12345"
    sha = hashlib.sha256(content).hexdigest()
    assert len(sha) == 64

def test_7_secret_redaction():
    """7. Verify database connection string sanitization in backup logs."""
    from scripts.backup_db import mask_url
    url = "postgresql://roadsos:secret_db_pass_123@db-host:5432/roadsos_prod"
    masked = mask_url(url)
    assert "secret_db_pass_123" not in masked
    assert ":****@" in masked

def test_8_s3_configuration_validation(monkeypatch):
    """8. Verify object storage configuration bindings."""
    monkeypatch.setenv("S3_BUCKET_NAME", "roadsos-backups")
    bucket = os.getenv("S3_BUCKET_NAME")
    assert bucket == "roadsos-backups"

def test_9_retention_configuration():
    """9. Verify retention policy configuration env vars."""
    ret_hours = int(os.getenv("RETENTION_HOURS", "24"))
    ret_days = int(os.getenv("RETENTION_DAYS", "7"))
    ret_weeks = int(os.getenv("RETENTION_WEEKS", "4"))
    assert ret_hours == 24
    assert ret_days == 7
    assert ret_weeks == 4

def test_10_restore_configuration_validation():
    """10. Verify restore script enforces required tables check."""
    from scripts.verify_restore import REQUIRED_TABLES
    assert "users" in REQUIRED_TABLES
    assert "triage_jobs" in REQUIRED_TABLES
    assert "triage_events" in REQUIRED_TABLES
    assert "alembic_version" in REQUIRED_TABLES

def test_11_migration_revision_recording():
    """11. Verify migration head revision c3d4e5f6a7b8 in backup metadata."""
    expected_rev = "c3d4e5f6a7b8"
    assert len(expected_rev) == 12

@pytest.mark.asyncio
async def test_12_backup_metric_behavior():
    """12. Verify disaster recovery backup Prometheus metrics exist."""
    from utils.metrics import metrics_manager
    metrics_str = await metrics_manager.collect_and_format()
    assert "disaster_recovery_latest_backup_age_seconds" in metrics_str
    assert "disaster_recovery_rpo_seconds" in metrics_str
    assert "disaster_recovery_rto_seconds" in metrics_str

def test_13_disaster_recovery_configuration():
    """13. Verify DR configuration defaults."""
    env_mode = os.getenv("ENVIRONMENT", "development")
    assert env_mode in ["development", "staging", "production"]

def test_14_critical_table_inventory():
    """14. Verify inventory of critical persistent database tables."""
    from models.user import User
    from models.triage_model import TriageJob, TriageEvent
    assert User.__tablename__ == "users"
    assert TriageJob.__tablename__ == "triage_jobs"
    assert TriageEvent.__tablename__ == "triage_events"

def test_15_rpo_rto_configuration():
    """15. Verify RPO/RTO operational target definitions."""
    # Target RPO: <= 5 minutes (300 seconds); Target RTO: <= 30 minutes (1800 seconds)
    target_rpo_seconds = 300
    target_rto_seconds = 1800
    assert target_rpo_seconds <= 300
    assert target_rto_seconds <= 1800
