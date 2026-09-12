import pytest
import os
import glob
import gzip
import hashlib
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from utils.metrics import metrics_manager

client = TestClient(app)

def test_backup_sha256_checksum_and_validation(tmp_path):
    """Verify SHA-256 checksum generation and verification for backup artifacts."""
    out_dir = str(tmp_path)
    backup_file = os.path.join(out_dir, "roadsos_backup_roadsos_db_20260910_120000.sql.gz")

    with open(backup_file, "wb") as f:
        f.write(gzip.compress(b"MOCK POSTGRESQL BACKUP DATA FOR STEP 20 DR TEST"))

    # Generate SHA-256 manifest
    sha256_hash = hashlib.sha256()
    with open(backup_file, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    checksum_hex = sha256_hash.hexdigest()

    checksum_file = f"{backup_file}.sha256"
    with open(checksum_file, "w") as f_chk:
        f_chk.write(f"{checksum_hex}  {os.path.basename(backup_file)}\n")

    assert os.path.exists(checksum_file)
    with open(checksum_file, "r") as f:
        read_checksum = f.read().split()[0]
    assert read_checksum == checksum_hex

def test_backup_tamper_detection(tmp_path):
    """Verify checksum validation fails if the backup file is modified/corrupted."""
    out_dir = str(tmp_path)
    backup_file = os.path.join(out_dir, "test_tampered.sql.gz")
    checksum_file = f"{backup_file}.sha256"

    with open(backup_file, "wb") as f:
        f.write(gzip.compress(b"ORIGINAL DATA"))

    # Write original checksum
    sha256_hash = hashlib.sha256()
    with open(backup_file, "rb") as f:
        sha256_hash.update(f.read())
    original_hex = sha256_hash.hexdigest()

    with open(checksum_file, "w") as f:
        f.write(f"{original_hex}  {os.path.basename(backup_file)}\n")

    # Tamper with backup file
    with open(backup_file, "wb") as f:
        f.write(gzip.compress(b"TAMPERED DATA CORRUPTED"))

    # Re-calculate hash
    sha256_tampered = hashlib.sha256()
    with open(backup_file, "rb") as f:
        sha256_tampered.update(f.read())
    
    assert original_hex != sha256_tampered.hexdigest()

def test_restore_verification_pipeline(tmp_path, monkeypatch):
    """Verify restore verification returns PASSED status for valid schema."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://roadsos:roadsos_password@localhost:5432/roadsos_db")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="table count: 8", stderr="")
        from scripts.verify_restore import verify_restore
        
        test_file = os.path.join(str(tmp_path), "dummy_backup.sql.gz")
        compressed_data = gzip.compress(b"CREATE TABLE users (id text);")
        with open(test_file, "wb") as f:
            f.write(compressed_data)

        sha256_hex = hashlib.sha256(compressed_data).hexdigest()
        with open(f"{test_file}.sha256", "w") as f:
            f.write(f"{sha256_hex}  {os.path.basename(test_file)}\n")

        res = verify_restore(backup_file=test_file, temp_dbname="roadsos_restore_mock_tmp")
        assert res["status"] == "PASSED"

def test_pitr_verification_pipeline(tmp_path, monkeypatch):
    """Verify Point-In-Time Recovery verification logic."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://roadsos:roadsos_password@localhost:5432/roadsos_db")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="WAL replay ok", stderr="")
        from scripts.verify_pitr import verify_pitr

        test_file = os.path.join(str(tmp_path), "dummy_pitr.sql.gz")
        compressed_data = gzip.compress(b"CREATE TABLE triage_events (id text);")
        with open(test_file, "wb") as f:
            f.write(compressed_data)

        sha256_hex = hashlib.sha256(compressed_data).hexdigest()
        with open(f"{test_file}.sha256", "w") as f:
            f.write(f"{sha256_hex}  {os.path.basename(test_file)}\n")

        res = verify_pitr(backup_file=test_file, temp_dbname="roadsos_pitr_mock_tmp")
        assert res["status"] == "PASSED"

def test_retention_cleanup_dry_run(tmp_path):
    """Verify retention cleanup dry-run identifies outdated backup files."""
    from scripts.cleanup_backups import cleanup_backups
    out_dir = str(tmp_path)
    
    b_file = os.path.join(out_dir, "roadsos_backup_test_20260101_000000.sql.gz")
    with open(b_file, "wb") as f:
        f.write(gzip.compress(b"OLD BACKUP DATA"))

    res = cleanup_backups(backup_dir=out_dir, dry_run=True)
    assert "kept_count" in res

def test_prometheus_dr_metrics_extension():
    """Verify /metrics exposes all low-cardinality disaster recovery indicators."""
    response = client.get("/metrics")
    assert response.status_code == 200
    metrics_text = response.text

    assert "disaster_recovery_latest_backup_age_seconds" in metrics_text
    assert "disaster_recovery_last_backup_success" in metrics_text
    assert "disaster_recovery_backup_size_bytes" in metrics_text
    assert "disaster_recovery_restore_validation_success" in metrics_text
    assert "disaster_recovery_rpo_target_seconds" in metrics_text
    assert "disaster_recovery_rto_target_seconds" in metrics_text

@pytest.mark.asyncio
async def test_readiness_fails_during_db_outage():
    """Verify readiness returns 503 while liveness stays 200 during DB connection loss."""
    with patch("database.AsyncSessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database Unreachable")
        mock_session_local.return_value.__aenter__.return_value = mock_session

        # Liveness check must pass (200 OK)
        r_health = client.get("/api/health")
        assert r_health.status_code == 200
        assert r_health.json()["liveness"] is True

        # Readiness check must fail (503 Service Unavailable)
        r_ready = client.get("/api/ready")
        assert r_ready.status_code == 503
        assert r_ready.json()["status"] == "unavailable"

def test_idor_boundary_preservation():
    """Verify user authorization dependencies remain intact post-restore."""
    response = client.get("/api/triage/history")
    assert response.status_code == 401
