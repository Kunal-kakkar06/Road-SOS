import os
import sys
import time
import logging
from typing import Dict, Any, Optional

from utils.logging_config import logger
from utils.metrics import metrics_manager
from scripts.backup_db import run_backup
from scripts.verify_restore import verify_restore
from scripts.cleanup_backups import cleanup_backups
from services.backup_replication_service import backup_replication_service

class BackupService:
    """
    Dedicated Disaster Recovery Backup & Validation Service.
    Wraps logical database backup generation, disposable restore validation,
    off-site replication, retention lifecycle cleanup, and Prometheus metrics tracking.
    """
    def __init__(self, backup_dir: str = "/tmp/roadsos_backups"):
        self.backup_dir = backup_dir

    def create_backup(self, compress: bool = True, replicate: bool = True) -> Dict[str, Any]:
        """
        Executes pg_dump snapshot backup, writes SHA-256 manifest, replicates off-site (if enabled),
        and records metrics. Fails safely without raising uncaught exceptions.
        """
        start_time = time.time()
        logger.info("Backup creation initiated", extra={"event_name": "disaster_recovery.backup.started"})

        try:
            backup_path = run_backup(output_dir=self.backup_dir, compress=compress)
            duration_s = round(time.time() - start_time, 3)
            size_bytes = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0

            logger.info(
                "Backup completed successfully",
                extra={
                    "event_name": "disaster_recovery.backup.completed",
                    "duration_ms": duration_s * 1000.0,
                    "status": "completed",
                    "extra_fields": {
                        "backup_file": os.path.basename(backup_path),
                        "size_bytes": size_bytes
                    }
                }
            )

            replication_result = None
            if replicate:
                replication_result = backup_replication_service.replicate_backup(backup_path)

            return {
                "status": "completed",
                "backup_path": backup_path,
                "duration_seconds": duration_s,
                "size_bytes": size_bytes,
                "replication": replication_result
            }

        except Exception as e:
            duration_s = round(time.time() - start_time, 3)
            logger.error(
                f"Backup execution failed: {e}",
                extra={
                    "event_name": "disaster_recovery.backup.failed",
                    "duration_ms": duration_s * 1000.0,
                    "status": "failed",
                    "extra_fields": {"error": str(e)}
                },
                exc_info=True
            )
            metrics_manager.record_db_error()
            return {
                "status": "failed",
                "error": str(e),
                "duration_seconds": duration_s
            }

    def verify_backup(self, backup_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Restores backup artifact into isolated temporary database to verify schema and row counts.
        """
        start_time = time.time()
        try:
            res = verify_restore(backup_file=backup_path, temp_dbname="roadsos_restore_verify_tmp")
            duration_s = round(time.time() - start_time, 3)

            logger.info(
                "Backup restore verification completed",
                extra={
                    "event_name": "disaster_recovery.restore.verified",
                    "duration_ms": duration_s * 1000.0,
                    "status": res.get("status", "unknown")
                }
            )
            return res
        except Exception as e:
            logger.error(f"Restore verification failed: {e}", extra={"event_name": "disaster_recovery.restore.failed"})
            return {"status": "failed", "error": str(e)}

    def verify_remote_backup(self, remote_key: str) -> Dict[str, Any]:
        """
        Downloads remote backup artifact from off-site storage, validates SHA-256 integrity,
        and executes disposable restore verification into isolated database `roadsos_remote_restore_tmp`.
        """
        dl_res = backup_replication_service.download_remote_backup(remote_key, dest_dir="/tmp/roadsos_remote_verify")
        if dl_res.get("status") != "completed":
            return dl_res

        local_path = dl_res["local_path"]
        try:
            restore_res = verify_restore(backup_file=local_path, temp_dbname="roadsos_remote_restore_tmp")
            return {
                "status": restore_res.get("status", "completed"),
                "remote_key": remote_key,
                "local_path": local_path,
                "sha256": dl_res.get("sha256"),
                "restore_result": restore_res
            }
        except Exception as e:
            logger.error(f"Remote restore verification failed: {e}", extra={"event_name": "disaster_recovery.remote_restore.failed"})
            return {"status": "failed", "error": str(e)}

    def cleanup_retention(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Cleans up outdated backup artifacts based on retention policy.
        """
        try:
            res = cleanup_backups(backup_dir=self.backup_dir, dry_run=dry_run)
            logger.info(
                "Backup retention cleanup executed",
                extra={
                    "event_name": "disaster_recovery.cleanup.completed",
                    "extra_fields": res
                }
            )
            return res
        except Exception as e:
            logger.error(f"Backup retention cleanup failed: {e}", extra={"event_name": "disaster_recovery.cleanup.failed"})
            return {"status": "failed", "error": str(e)}

# Global backup service instance
backup_service = BackupService()

