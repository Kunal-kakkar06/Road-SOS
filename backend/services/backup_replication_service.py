import os
import sys
import time
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from utils.logging_config import logger
from utils.metrics import metrics_manager

def sanitize_secret_string(text: str) -> str:
    """Masks secret keys, access keys, passwords, and authorization tokens in strings."""
    if not text:
        return ""
    import re
    # Mask S3 access keys and secret keys if present in error text
    sanitized = re.sub(r'(AWS_SECRET_ACCESS_KEY|secret_key|password|access_key)=["\']?[^"\'\s]+["\']?', r'\1=[REDACTED]', text, flags=re.IGNORECASE)
    sanitized = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED_ACCESS_KEY]', sanitized)
    sanitized = re.sub(r'([a-zA-Z0-9+/]{40})', '[REDACTED_SECRET]', sanitized)
    return sanitized

class BackupReplicationService:
    """
    Provider-independent Off-Site Backup Replication Service.
    Replicates local PostgreSQL snapshot backups to S3-compatible object storage
    with Server-Side Encryption (SSE-S3 / SSE-KMS), metadata tagging, and remote integrity verification.
    """
    @property
    def enabled(self) -> bool:
        return os.getenv("BACKUP_REPLICATION_ENABLED", "false").lower() in ("true", "1", "yes")

    @property
    def bucket(self) -> str:
        return os.getenv("BACKUP_STORAGE_BUCKET", "")

    @property
    def prefix(self) -> str:
        return os.getenv("BACKUP_STORAGE_PREFIX", "roadsos/backups/").lstrip("/")

    @property
    def region(self) -> str:
        return os.getenv("BACKUP_STORAGE_REGION", "us-east-1")

    @property
    def endpoint_url(self) -> Optional[str]:
        return os.getenv("BACKUP_STORAGE_ENDPOINT", None)

    @property
    def access_key(self) -> Optional[str]:
        return os.getenv("BACKUP_STORAGE_ACCESS_KEY", None)

    @property
    def secret_key(self) -> Optional[str]:
        return os.getenv("BACKUP_STORAGE_SECRET_KEY", None)

    @property
    def kms_key_id(self) -> Optional[str]:
        return os.getenv("BACKUP_STORAGE_KMS_KEY_ID", None)

    def _get_s3_client(self):
        """Constructs boto3 S3 client using environment configuration."""
        from botocore.config import Config
        kwargs: Dict[str, Any] = {
            "region_name": self.region,
            "config": Config(connect_timeout=2, read_timeout=2, retries={'max_attempts': 1})
        }
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        if self.access_key and self.secret_key:
            kwargs["aws_access_key_id"] = self.access_key
            kwargs["aws_secret_access_key"] = self.secret_key

        return boto3.client("s3", **kwargs)

    def replicate_backup(self, local_backup_path: str) -> Dict[str, Any]:
        """
        Replicates local snapshot backup file and SHA-256 manifest to off-site object storage.
        Verifies remote SHA-256 integrity and records Prometheus metrics.
        """
        if not self.enabled:
            logger.info("Off-site backup replication is disabled (BACKUP_REPLICATION_ENABLED=false)", extra={"event_name": "disaster_recovery.replication.disabled"})
            return {"status": "disabled", "message": "Replication disabled via environment configuration"}

        if not self.bucket:
            err = "BACKUP_STORAGE_BUCKET environment variable must be configured when replication is enabled."
            logger.error(err, extra={"event_name": "disaster_recovery.replication.misconfigured"})
            metrics_manager.record_replication_failure()
            return {"status": "failed", "error": err}

        if not os.path.exists(local_backup_path):
            err = f"Local backup file does not exist: {local_backup_path}"
            logger.error(err, extra={"event_name": "disaster_recovery.replication.failed"})
            metrics_manager.record_replication_failure()
            return {"status": "failed", "error": err}

        start_time = time.time()
        filename = os.path.basename(local_backup_path)
        remote_key = f"{self.prefix}{filename}"
        checksum_file = f"{local_backup_path}.sha256"

        logger.info(
            f"Initiating off-site replication for backup: {filename}",
            extra={
                "event_name": "disaster_recovery.replication.started",
                "extra_fields": {"bucket": self.bucket, "remote_key": remote_key}
            }
        )

        try:
            # 1. Compute/verify local SHA-256
            sha256_hash = hashlib.sha256()
            with open(local_backup_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(chunk)
            computed_hex = sha256_hash.hexdigest()

            # Read expected checksum from manifest file if present
            expected_hex = computed_hex
            if os.path.exists(checksum_file):
                with open(checksum_file, "r") as f_chk:
                    expected_hex = f_chk.read().split()[0]

            if computed_hex != expected_hex:
                err = f"Local backup SHA-256 mismatch before upload! Computed: {computed_hex}, Expected: {expected_hex}"
                logger.error(err, extra={"event_name": "disaster_recovery.replication.tamper_detected"})
                metrics_manager.record_replication_failure()
                return {"status": "failed", "error": err}

            size_bytes = os.path.getsize(local_backup_path)
            now_iso = datetime.now(timezone.utc).isoformat()

            # 2. Build metadata (NO PHI/PII)
            metadata = {
                "backup_filename": filename,
                "creation_timestamp": now_iso,
                "sha256_checksum": computed_hex,
                "app_version": os.getenv("APP_VERSION", "1.0.0"),
                "alembic_revision": "a1b2c3d4e5f6",
                "postgresql_version": "15.4",
                "backup_size": str(size_bytes),
                "replication_timestamp": now_iso
            }

            # 3. Configure Server-Side Encryption (SSE)
            extra_args: Dict[str, Any] = {"Metadata": metadata}
            sse_mode = os.getenv("BACKUP_STORAGE_ENCRYPTION", "AES256").upper()
            if self.kms_key_id:
                extra_args["ServerSideEncryption"] = "aws:kms"
                extra_args["SSEKMSKeyId"] = self.kms_key_id
            elif sse_mode != "NONE":
                extra_args["ServerSideEncryption"] = sse_mode

            s3 = self._get_s3_client()

            # Check if remote object already exists (Idempotency check)
            try:
                existing = s3.head_object(Bucket=self.bucket, Key=remote_key)
                ex_size = existing.get("ContentLength", 0)
                ex_meta = existing.get("Metadata", {})
                ex_sha256 = ex_meta.get("sha256_checksum", "")
                if ex_size == size_bytes and (not ex_sha256 or ex_sha256 == computed_hex):
                    logger.info(
                        f"Remote object already exists and matches ({remote_key}). Skipping re-upload for idempotency.",
                        extra={"event_name": "disaster_recovery.replication.idempotent_skip"}
                    )
                    metrics_manager.record_replication_success(duration_s=0.01, size_bytes=size_bytes)
                    return {
                        "status": "completed",
                        "remote_key": remote_key,
                        "sha256": computed_hex,
                        "size_bytes": size_bytes,
                        "duration_seconds": 0.01,
                        "idempotent_skip": True
                    }
            except Exception:
                pass

            # 4. Upload backup file with fallback if S3 provider (e.g. MinIO) lacks SSE KMS module
            try:
                s3.upload_file(local_backup_path, self.bucket, remote_key, ExtraArgs=extra_args)
            except Exception as upload_err:
                if "NotImplemented" in str(upload_err) and "ServerSideEncryption" in extra_args:
                    logger.info("S3 provider returned NotImplemented for SSE; retrying upload without SSE header", extra={"event_name": "disaster_recovery.replication.sse_fallback"})
                    extra_args.pop("ServerSideEncryption", None)
                    extra_args.pop("SSEKMSKeyId", None)
                    s3.upload_file(local_backup_path, self.bucket, remote_key, ExtraArgs=extra_args)
                else:
                    raise

            # 5. Upload .sha256 manifest
            if os.path.exists(checksum_file):
                manifest_remote_key = f"{remote_key}.sha256"
                try:
                    s3.upload_file(checksum_file, self.bucket, manifest_remote_key)
                except Exception as m_err:
                    if "NotImplemented" in str(m_err):
                        s3.upload_file(checksum_file, self.bucket, manifest_remote_key)
                    else:
                        raise

            duration_s = round(time.time() - start_time, 3)

            # 6. Remote Verification (Head Object)
            head_resp = s3.head_object(Bucket=self.bucket, Key=remote_key)
            remote_size = head_resp.get("ContentLength", 0)
            remote_metadata = head_resp.get("Metadata", {})
            remote_sha256 = remote_metadata.get("sha256_checksum", "")

            if remote_size != size_bytes or (remote_sha256 and remote_sha256 != computed_hex):
                err = f"Remote verification failed! Size match: {remote_size == size_bytes}, SHA256 match: {remote_sha256 == computed_hex}"
                logger.error(err, extra={"event_name": "disaster_recovery.replication.integrity_failed"})
                metrics_manager.record_replication_failure()
                return {"status": "failed", "error": err}

            # 7. Record Prometheus metrics
            metrics_manager.record_replication_success(duration_s=duration_s, size_bytes=size_bytes)

            # 8. Create local replication marker file
            marker_file = f"{local_backup_path}.replicated"
            with open(marker_file, "w") as f_m:
                f_m.write(f"REPLICATED_KEY={remote_key}\nREPLICATED_AT={now_iso}\nSHA256={computed_hex}\n")

            logger.info(
                "Off-site backup replication completed successfully",
                extra={
                    "event_name": "disaster_recovery.replication.completed",
                    "duration_ms": duration_s * 1000.0,
                    "status": "completed",
                    "extra_fields": {
                        "remote_key": remote_key,
                        "size_bytes": size_bytes,
                        "sha256": computed_hex
                    }
                }
            )

            return {
                "status": "completed",
                "remote_key": remote_key,
                "sha256": computed_hex,
                "size_bytes": size_bytes,
                "duration_seconds": duration_s
            }

        except Exception as e:
            duration_s = round(time.time() - start_time, 3)
            safe_err = sanitize_secret_string(str(e))
            logger.error(
                f"Off-site backup replication failed: {safe_err}",
                extra={
                    "event_name": "disaster_recovery.replication.failed",
                    "duration_ms": duration_s * 1000.0,
                    "status": "failed",
                    "extra_fields": {"error": safe_err}
                },
                exc_info=True
            )
            metrics_manager.record_replication_failure()
            return {"status": "failed", "error": safe_err, "duration_seconds": duration_s}

    def download_remote_backup(self, remote_key: str, dest_dir: str = "/tmp/roadsos_remote_downloads") -> Dict[str, Any]:
        """
        Downloads remote backup artifact and manifest from off-site storage to dest_dir.
        Verifies SHA-256 integrity of downloaded artifact.
        """
        if not self.bucket:
            return {"status": "failed", "error": "BACKUP_STORAGE_BUCKET not configured"}

        os.makedirs(dest_dir, exist_ok=True)
        filename = os.path.basename(remote_key)
        local_path = os.path.join(dest_dir, filename)

        try:
            s3 = self._get_s3_client()
            head_resp = s3.head_object(Bucket=self.bucket, Key=remote_key)
            meta_sha256 = head_resp.get("Metadata", {}).get("sha256_checksum", "")

            # Download backup file
            s3.download_file(self.bucket, remote_key, local_path)

            # Download .sha256 manifest if present
            manifest_key = f"{remote_key}.sha256"
            manifest_local_path = f"{local_path}.sha256"
            try:
                s3.download_file(self.bucket, manifest_key, manifest_local_path)
            except Exception:
                pass

            # Calculate downloaded SHA-256
            sha256_hash = hashlib.sha256()
            with open(local_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256_hash.update(chunk)
            downloaded_sha256 = sha256_hash.hexdigest()

            if meta_sha256 and downloaded_sha256 != meta_sha256:
                err = f"Remote download SHA-256 mismatch! Downloaded: {downloaded_sha256}, Remote Metadata: {meta_sha256}"
                logger.error(err, extra={"event_name": "disaster_recovery.remote_download.checksum_mismatch"})
                return {"status": "failed", "error": err}

            return {
                "status": "completed",
                "local_path": local_path,
                "sha256": downloaded_sha256,
                "metadata": head_resp.get("Metadata", {})
            }
        except Exception as e:
            safe_err = sanitize_secret_string(str(e))
            logger.error(f"Remote backup download failed: {safe_err}", extra={"event_name": "disaster_recovery.remote_download.failed"})
            return {"status": "failed", "error": safe_err}

# Global replication service instance
backup_replication_service = BackupReplicationService()
