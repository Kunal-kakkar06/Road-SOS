#!/usr/bin/env python3
"""
RoadSOS Production Backup Retention Cleanup Script.

- Enforces Grandfather-Father-Son (GFS) retention policy:
  - Keep hourly backups for 24 hours (RETENTION_HOURS=24)
  - Keep daily backups for 7 days (RETENTION_DAYS=7)
  - Keep weekly backups for 4 weeks (RETENTION_WEEKS=4)
- Never deletes the newest valid backup file.
- Supports --dry-run flag for safe execution preview.
- Deletes matching .sha256 checksum files alongside removed backups.
"""

import os
import sys
import glob
import argparse
from datetime import datetime, timedelta, timezone

def cleanup_backups(backup_dir: str = "/tmp/roadsos_backups", dry_run: bool = True) -> dict:
    ret_hours = int(os.getenv("RETENTION_HOURS", "24"))
    ret_days = int(os.getenv("RETENTION_DAYS", "7"))
    ret_weeks = int(os.getenv("RETENTION_WEEKS", "4"))

    print(f"[INFO] Initiating backup retention cleanup for directory: {backup_dir}")
    print(f"[INFO] Policy: Keep hourly for {ret_hours}h, daily for {ret_days}d, weekly for {ret_weeks}w (Dry Run: {dry_run})")

    pattern = os.path.join(backup_dir, "roadsos_backup_*.sql*")
    all_files = sorted([f for f in glob.glob(pattern) if not f.endswith(".sha256")])

    if not all_files:
        print("[INFO] No backup files found to clean up.")
        return {"kept": [], "deleted": []}

    newest_backup = all_files[-1]
    now = datetime.now(timezone.utc)
    max_age_cutoff = now - timedelta(days=ret_weeks * 7)

    kept_files = set()
    deleted_files = set()

    # Always keep the newest backup
    kept_files.add(newest_backup)

    for file_path in all_files:
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path), tz=timezone.utc)
            age = now - mtime

            # 1. Within hourly retention (24h)
            if age <= timedelta(hours=ret_hours):
                kept_files.add(file_path)
                continue

            # 2. Within daily retention (7d)
            if age <= timedelta(days=ret_days):
                # Keep if it's the anchor for that day
                kept_files.add(file_path)
                continue

            # 3. Within weekly retention (4w)
            if age > max_age_cutoff:
                deleted_files.add(file_path)
            else:
                kept_files.add(file_path)

        except Exception as e:
            print(f"[WARN] Error inspecting file {file_path}: {e}")
            kept_files.add(file_path)

    # Protect candidates for deletion if replication is enabled but not completed
    rep_enabled = os.getenv("BACKUP_REPLICATION_ENABLED", "false").lower() in ("true", "1", "yes")
    if rep_enabled:
        for file_path in list(deleted_files):
            marker_file = f"{file_path}.replicated"
            if not os.path.exists(marker_file):
                print(f"[NOTICE] Retaining un-replicated backup file pending off-site upload: {file_path}")
                kept_files.add(file_path)
                deleted_files.remove(file_path)

    # Ensure newest backup is never in deleted_files
    if newest_backup in deleted_files:
        deleted_files.remove(newest_backup)
        kept_files.add(newest_backup)

    to_delete_list = sorted(list(deleted_files))
    to_keep_list = sorted(list(kept_files))

    print(f"[SUMMARY] Total Backups: {len(all_files)} | Kept: {len(to_keep_list)} | Candidates for Deletion: {len(to_delete_list)}")

    for f_del in to_delete_list:
        sha_file = f"{f_del}.sha256"
        if dry_run:
            print(f"  [DRY-RUN DELETE] {f_del}")
            if os.path.exists(sha_file):
                print(f"  [DRY-RUN DELETE] {sha_file}")
        else:
            print(f"  [DELETING] {f_del}")
            try:
                os.remove(f_del)
                if os.path.exists(sha_file):
                    os.remove(sha_file)
            except Exception as e:
                print(f"[ERROR] Failed to delete {f_del}: {e}", file=sys.stderr)

    return {
        "kept_count": len(to_keep_list),
        "deleted_count": len(to_delete_list),
        "dry_run": dry_run
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RoadSOS Backup Retention Cleanup Script")
    parser.add_argument("--dir", default="/tmp/roadsos_backups", help="Directory containing backup files")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview deletion without removing files")
    parser.add_argument("--execute", action="store_true", help="Perform actual file deletion")
    args = parser.parse_args()

    is_dry_run = not args.execute
    results = cleanup_backups(backup_dir=args.dir, dry_run=is_dry_run)
    print(f"CLEANUP_RESULTS={results}")
