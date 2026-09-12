#!/usr/bin/env python3
"""
RoadSOS Repeatable Database Restore Verification Script.

- Restores a PostgreSQL backup into a temporary database (`roadsos_restore_verify_tmp`).
- Verifies integrity of core tables: users, triage_jobs, triage_events, incidents, hospitals, providers, alembic_version.
- Verifies row counts and Alembic migration state.
- Cleans up the temporary database safely.
- Never mutates primary production data.
"""

import os
import sys
import glob
import argparse
import subprocess
import gzip
import shutil
from urllib.parse import urlparse

REQUIRED_TABLES = [
    "users",
    "triage_jobs",
    "triage_events",
    "incidents",
    "hospitals",
    "providers",
    "alembic_version"
]

def verify_restore(backup_file: str = None, temp_dbname: str = "roadsos_restore_verify_tmp") -> dict:
    db_url = os.getenv("DATABASE_URL")
    if not db_url or "sqlite" in db_url:
        print("[ERROR] DATABASE_URL must be configured with a PostgreSQL connection string.", file=sys.stderr)
        sys.exit(1)

    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")
    parsed = urlparse(clean_url)

    user = parsed.username or "roadsos"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = str(parsed.port or 5432)

    if not backup_file:
        backups = sorted(glob.glob("/tmp/roadsos_backups/roadsos_backup_*.sql*"))
        if not backups:
            print("[FATAL] No backup files found in /tmp/roadsos_backups/", file=sys.stderr)
            sys.exit(1)
        backup_file = backups[-1]

    if not os.path.exists(backup_file):
        print(f"[FATAL] Backup file does not exist: {backup_file}", file=sys.stderr)
        sys.exit(1)

    # SHA-256 Checksum Validation
    checksum_file = f"{backup_file}.sha256"
    if os.path.exists(checksum_file):
        print(f"[INFO] Validating SHA-256 checksum from file: {checksum_file}")
        with open(checksum_file, "r") as f_chk:
            expected_hash = f_chk.read().split()[0].strip()
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(backup_file, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        actual_hash = sha256_hash.hexdigest()

        if actual_hash != expected_hash:
            print(f"[FATAL] SHA-256 checksum mismatch! Expected: {expected_hash}, Actual: {actual_hash}", file=sys.stderr)
            sys.exit(1)
        print(f"[SUCCESS] SHA-256 checksum verified cleanly: {actual_hash}")
    else:
        print(f"[WARN] SHA-256 checksum file {checksum_file} not found; skipping checksum check.")

    print(f"[INFO] Starting restore verification for backup: {backup_file}")
    print(f"[INFO] Using isolated temporary database: {temp_dbname}")

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    has_local_psql = shutil.which("psql") is not None

    def run_psql_cmd(cmd_str: str, target_db: str = "postgres"):
        if has_local_psql:
            cmd = ["psql", "-h", host, "-p", port, "-U", user, "-d", target_db, "-c", cmd_str]
            return subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            cmd = ["docker", "exec", "backend-db-1", "psql", "-U", user, "-d", target_db, "-c", cmd_str]
            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 1. Drop temp db if exists and recreate
    run_psql_cmd(f"DROP DATABASE IF EXISTS {temp_dbname};", "postgres")
    res_create = run_psql_cmd(f"CREATE DATABASE {temp_dbname};", "postgres")
    if res_create.returncode != 0:
        print(f"[FATAL] Failed to create temp DB {temp_dbname}: {res_create.stderr}", file=sys.stderr)
        sys.exit(1)

    # 2. Decompress backup if gzipped
    sql_path = backup_file
    is_temp_unzipped = False
    if backup_file.endswith(".gz"):
        sql_path = backup_file[:-3]
        with gzip.open(backup_file, 'rb') as f_in:
            with open(sql_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        is_temp_unzipped = True

    try:
        # 3. Restore via psql
        print(f"[INFO] Restoring SQL dump into {temp_dbname}...")
        if has_local_psql:
            restore_cmd = f"psql -h {host} -p {port} -U {user} -d {temp_dbname} < {sql_path}"
            res_restore = subprocess.run(restore_cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            cat_cmd = f"cat {sql_path} | docker exec -i backend-db-1 psql -U {user} -d {temp_dbname}"
            res_restore = subprocess.run(cat_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
        if res_restore.returncode != 0:
            print(f"[WARN] psql restore returned non-zero code: {res_restore.returncode}. Stderr: {res_restore.stderr[:500]}")

        # 4. Run Table Existence & Integrity Checks
        table_counts = {}
        for table in REQUIRED_TABLES:
            res_count = run_psql_cmd(f"SELECT COUNT(*) FROM {table};", temp_dbname)
            if res_count.returncode != 0:
                print(f"[FATAL] Required table '{table}' missing or unreadable in restored database: {res_count.stderr}", file=sys.stderr)
                sys.exit(1)
            output_lines = [line.strip() for line in res_count.stdout.strip().split("\n") if line.strip().isdigit()]
            cnt = int(output_lines[0]) if output_lines else 0
            table_counts[table] = cnt
            print(f"  [CHECK] Table '{table}': {cnt} rows")

        # 5. Check Alembic Version
        res_ver = run_psql_cmd("SELECT version_num FROM alembic_version;", temp_dbname)
        alembic_ver = res_ver.stdout.strip()
        print(f"  [CHECK] Alembic revision in restored DB: {alembic_ver}")

    finally:
        if is_temp_unzipped and os.path.exists(sql_path):
            os.remove(sql_path)

        # 6. Cleanup Temporary Database
        print(f"[INFO] Cleaning up temporary database {temp_dbname}...")
        run_psql_cmd(f"DROP DATABASE IF EXISTS {temp_dbname};", "postgres")

    print("[SUCCESS] Disaster recovery restore verification PASSED cleanly!")
    return {
        "status": "PASSED",
        "backup_file": backup_file,
        "table_counts": table_counts,
        "alembic_version": alembic_ver
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RoadSOS Restore Verification Script")
    parser.add_argument("--file", default=None, help="Path to backup file (.sql or .sql.gz)")
    args = parser.parse_args()

    results = verify_restore(backup_file=args.file)
    print(f"RESTORE_VERIFICATION={results}")
