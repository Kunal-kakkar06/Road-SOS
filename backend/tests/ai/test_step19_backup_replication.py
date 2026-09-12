import os
import pytest
import shutil
import hashlib
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from services.backup_replication_service import BackupReplicationService, sanitize_secret_string
from services.backup_service import BackupService
from services.object_storage import ObjectStorageService
from models.backup_replica import BackupReplica
from database import AsyncSessionLocal

client = TestClient(app)

def test_replication_disabled_by_default(monkeypatch):
    monkeypatch.delenv("BACKUP_REPLICATION_ENABLED", raising=False)
    service = BackupReplicationService()
    res = service.replicate_backup("/tmp/dummy_backup.sql.gz")
    assert res["status"] == "disabled"

def test_missing_bucket_rejected_safely(monkeypatch):
    monkeypatch.setenv("BACKUP_REPLICATION_ENABLED", "true")
    monkeypatch.setenv("BACKUP_STORAGE_BUCKET", "")
    service = BackupReplicationService()
    res = service.replicate_backup("/tmp/dummy_backup.sql.gz")
    assert res["status"] == "failed"
    assert "BACKUP_STORAGE_BUCKET" in res["error"]

def test_secret_redaction_in_logs():
    raw_error = "AccessDenied: AKIAIOSFODNN7EXAMPLE secret_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    sanitized = sanitize_secret_string(raw_error)
    assert "wJalrXUtnFEMI" not in sanitized
    assert "[REDACTED" in sanitized

def test_replication_sha256_metadata_and_integrity(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_REPLICATION_ENABLED", "true")
    monkeypatch.setenv("BACKUP_STORAGE_BUCKET", "roadsos-test-bucket")
    
    out_dir = str(tmp_path)
    b_file = os.path.join(out_dir, "roadsos_backup_test_20260910_120000.sql.gz")
    b_content = b"SAMPLE BACKUP DATA FOR STEP 19 TEST"
    with open(b_file, "wb") as f:
        f.write(b_content)

    sha256_hex = hashlib.sha256(b_content).hexdigest()
    with open(f"{b_file}.sha256", "w") as f:
        f.write(f"{sha256_hex}  {os.path.basename(b_file)}\n")

    service = BackupReplicationService()
    mock_s3 = MagicMock()
    mock_s3.head_object.side_effect = [
        Exception("NotFound"),  # First head check for idempotency
        {"ContentLength": len(b_content), "Metadata": {"sha256_checksum": sha256_hex}} # Post-upload check
    ]

    with patch.object(service, "_get_s3_client", return_value=mock_s3):
        res = service.replicate_backup(b_file)
        assert res["status"] == "completed"
        assert res["sha256"] == sha256_hex
        assert os.path.exists(f"{b_file}.replicated")

def test_idempotent_duplicate_upload_prevention(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_REPLICATION_ENABLED", "true")
    monkeypatch.setenv("BACKUP_STORAGE_BUCKET", "roadsos-test-bucket")

    out_dir = str(tmp_path)
    b_file = os.path.join(out_dir, "roadsos_backup_idempotent.sql.gz")
    b_content = b"IDEMPOTENT BACKUP CONTENT"
    with open(b_file, "wb") as f:
        f.write(b_content)

    sha256_hex = hashlib.sha256(b_content).hexdigest()

    service = BackupReplicationService()
    mock_s3 = MagicMock()
    mock_s3.head_object.return_value = {
        "ContentLength": len(b_content),
        "Metadata": {"sha256_checksum": sha256_hex}
    }

    with patch.object(service, "_get_s3_client", return_value=mock_s3):
        res = service.replicate_backup(b_file)
        assert res["status"] == "completed"
        assert res.get("idempotent_skip") is True
        mock_s3.upload_file.assert_not_called()

def test_local_tampering_blocks_upload(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_REPLICATION_ENABLED", "true")
    monkeypatch.setenv("BACKUP_STORAGE_BUCKET", "roadsos-test-bucket")

    out_dir = str(tmp_path)
    b_file = os.path.join(out_dir, "roadsos_backup_tampered.sql.gz")
    with open(b_file, "wb") as f:
        f.write(b"REAL DATA")

    # Mismatched sha256 manifest
    with open(f"{b_file}.sha256", "w") as f:
        f.write("0000000000000000000000000000000000000000000000000000000000000000  roadsos_backup_tampered.sql.gz\n")

    service = BackupReplicationService()
    res = service.replicate_backup(b_file)
    assert res["status"] == "failed"
    assert "SHA-256 mismatch" in res["error"]

def test_replication_failure_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_REPLICATION_ENABLED", "true")
    monkeypatch.setenv("BACKUP_STORAGE_BUCKET", "roadsos-test-bucket")

    out_dir = str(tmp_path)
    b_file = os.path.join(out_dir, "roadsos_backup_outage.sql.gz")
    with open(b_file, "wb") as f:
        f.write(b"VALID DATA")

    service = BackupReplicationService()
    with patch.object(service, "_get_s3_client", side_effect=Exception("S3 Storage Outage 503")):
        res = service.replicate_backup(b_file)
        assert res["status"] == "failed"
        assert "S3 Storage Outage" in res["error"]
        assert os.path.exists(b_file)  # Local backup is preserved

def test_object_storage_service_abstraction():
    storage = ObjectStorageService(
        endpoint_url="http://localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="roadsos-test-bucket"
    )
    assert storage.bucket == "roadsos-test-bucket"
    assert storage.prefix == "roadsos/backups/"

@pytest.mark.asyncio
async def test_backup_replica_orm_model():
    import uuid
    b_id = f"test_backup_{uuid.uuid4()}"
    replica = BackupReplica(
        backup_id=b_id,
        storage_provider="s3",
        bucket="roadsos-test-bucket",
        object_key=f"roadsos/backups/{b_id}.sql.gz",
        region="us-east-1",
        encryption_mode="AES256",
        remote_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        remote_size_bytes=2048,
        status="VERIFIED"
    )
    async with AsyncSessionLocal() as db:
        db.add(replica)
        await db.commit()

        from sqlalchemy import select
        res = await db.execute(select(BackupReplica).where(BackupReplica.backup_id == b_id))
        fetched = res.scalars().first()
        assert fetched is not None
        assert fetched.status == "VERIFIED"
        assert fetched.remote_size_bytes == 2048

def test_api_metrics_includes_replication_indicators():
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text

    assert "disaster_recovery_replication_last_success" in metrics_text
    assert "disaster_recovery_replication_last_duration_seconds" in metrics_text
    assert "disaster_recovery_replication_last_backup_size_bytes" in metrics_text
    assert "disaster_recovery_replication_latest_backup_age_seconds" in metrics_text
    assert "disaster_recovery_replication_failures_total" in metrics_text
    assert "disaster_recovery_remote_uploads_total" in metrics_text
    assert "disaster_recovery_remote_verifications_total" in metrics_text
    assert "disaster_recovery_remote_upload_failures_total" in metrics_text
    assert "disaster_recovery_remote_backup_age_seconds" in metrics_text
    assert "disaster_recovery_remote_restore_duration_seconds" in metrics_text
    assert "disaster_recovery_remote_storage_available" in metrics_text
    assert "disaster_recovery_rpo_seconds" in metrics_text
    assert "disaster_recovery_rto_seconds" in metrics_text

def test_api_ready_includes_backup_replication_check():
    response = client.get("/api/ready")
    assert response.status_code == 200
    data = response.json()
    assert "checks" in data
    assert "backup_replication" in data["checks"]
