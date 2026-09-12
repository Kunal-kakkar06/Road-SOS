import os
import sys
import glob
import time
import gzip
import shutil
import hashlib
import json
import subprocess
from urllib.parse import urlparse

def run_physical_restore_verification():
    print("==================================================================")
    print("   ROADSOS STEP 23: PHYSICAL DATABASE RESTORE & DATA INTEGRITY    ")
    print("==================================================================")

    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://roadsos:roadsos_password@localhost:5432/roadsos_db")
    print(f"[1/6] Verifying PostgreSQL Primary Connection: {db_url}")
    assert "postgresql" in db_url, "Must use PostgreSQL for physical restore verification"

    clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")
    parsed = urlparse(clean_url)

    user = parsed.username or "roadsos"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = str(parsed.port or 5432)
    dbname = parsed.path.lstrip("/") or "roadsos_db"
    temp_dbname = "roadsos_restore_verify_tmp"

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    has_local_psql = shutil.which("psql") is not None

    def run_psql(cmd_str: str, target_db: str = "postgres"):
        if has_local_psql:
            cmd = ["psql", "-h", host, "-p", port, "-U", user, "-d", target_db, "-c", cmd_str]
            return subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            cmd = ["docker", "exec", "backend-db-1", "psql", "-U", user, "-d", target_db, "-c", cmd_str]
            return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 2. Query primary database row counts
    print("\n[2/6] Querying Primary Database Row Counts")
    critical_tables = ["users", "triage_jobs", "triage_events", "incidents", "hospitals", "providers", "alembic_version"]
    source_counts = {}
    for table in critical_tables:
        res = run_psql(f"SELECT COUNT(*) FROM {table};", dbname)
        lines = [line.strip() for line in res.stdout.strip().split("\n") if line.strip().isdigit()]
        source_counts[table] = int(lines[0]) if lines else 0
        print(f"      Primary Table '{table}': {source_counts[table]} rows")

    # 3. Locate / Execute Fresh Backup
    print("\n[3/6] Executing Fresh PostgreSQL Backup via backup_db.py")
    t0_backup = time.perf_counter()
    from scripts.backup_db import run_backup
    backup_file = run_backup(output_dir="/tmp/roadsos_backups", compress=True)
    backup_duration = time.perf_counter() - t0_backup
    print(f"      Backup Completed in {backup_duration:.2f}s -> {backup_file}")

    # Verify Checksum & Metadata
    checksum_file = f"{backup_file}.sha256"
    meta_file = f"{backup_file}.json"
    assert os.path.exists(checksum_file), f"SHA-256 file missing: {checksum_file}"
    assert os.path.exists(meta_file), f"JSON metadata file missing: {meta_file}"

    with open(checksum_file, "r") as f_chk:
        expected_hash = f_chk.read().split()[0].strip()
    
    sha256_hash = hashlib.sha256()
    with open(backup_file, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    actual_hash = sha256_hash.hexdigest()
    assert actual_hash == expected_hash, f"SHA-256 mismatch: {actual_hash} vs {expected_hash}"
    print(f"      SHA-256 Integrity Verified -> {actual_hash}")

    with open(meta_file, "r") as f_meta:
        meta_data = json.load(f_meta)
        print(f"      Companion Metadata -> ID: {meta_data.get('backup_id')}, Migration Revision: {meta_data.get('migration_revision')}")

    # 4. Provision Isolated Restore Database & Execute Restore
    print(f"\n[4/6] Restoring Snapshot into Isolated Database: {temp_dbname}")
    run_psql(f"DROP DATABASE IF EXISTS {temp_dbname};", "postgres")
    res_create = run_psql(f"CREATE DATABASE {temp_dbname};", "postgres")
    assert res_create.returncode == 0, f"Failed to create temp DB: {res_create.stderr}"

    sql_path = backup_file[:-3] if backup_file.endswith(".gz") else backup_file
    if backup_file.endswith(".gz"):
        with gzip.open(backup_file, 'rb') as f_in:
            with open(sql_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    t0_restore = time.perf_counter()
    try:
        if has_local_psql:
            restore_cmd = f"psql -h {host} -p {port} -U {user} -d {temp_dbname} < {sql_path}"
            res_rest = subprocess.run(restore_cmd, shell=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            cat_cmd = f"cat {sql_path} | docker exec -i backend-db-1 psql -U {user} -d {temp_dbname}"
            res_rest = subprocess.run(cat_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        restore_duration = time.perf_counter() - t0_restore
        print(f"      Restore Executed in {restore_duration:.2f}s")
    finally:
        if backup_file.endswith(".gz") and os.path.exists(sql_path):
            os.remove(sql_path)

    # 5. Data Integrity Audit & Count Comparison
    print("\n[5/6] Auditing Restored Database Schema & Data Integrity")
    restored_counts = {}
    mismatches = []
    for table in critical_tables:
        res = run_psql(f"SELECT COUNT(*) FROM {table};", temp_dbname)
        lines = [line.strip() for line in res.stdout.strip().split("\n") if line.strip().isdigit()]
        cnt = int(lines[0]) if lines else 0
        restored_counts[table] = cnt
        status = "MATCH" if cnt == source_counts[table] else "MISMATCH"
        print(f"      Restored Table '{table}': {cnt} rows (Source: {source_counts[table]}) -> {status}")
        if status == "MISMATCH":
            mismatches.append(table)

    assert not mismatches, f"Row count mismatches detected in tables: {mismatches}"

    # Verify Alembic Version in Restored DB
    res_ver = run_psql("SELECT version_num FROM alembic_version;", temp_dbname)
    alembic_ver = res_ver.stdout.strip()
    assert "c3d4e5f6a7b8" in alembic_ver, f"Unexpected restored Alembic version: {alembic_ver}"
    print(f"      Alembic Migration Head in Restored DB -> c3d4e5f6a7b8 (MATCH)")

    # 6. Cleanup Temporary Database
    print(f"\n[6/6] Cleaning Up Temporary Database: {temp_dbname}")
    run_psql(f"DROP DATABASE IF EXISTS {temp_dbname};", "postgres")

    print("\n==================================================================")
    print("   SUCCESS: PHYSICAL DATABASE RESTORE & DATA INTEGRITY PASSED!    ")
    print(f"   Measured Backup Duration:  {backup_duration:.2f}s (RPO Target: <= 5m)")
    print(f"   Measured Restore Duration: {restore_duration:.2f}s (RTO Target: <= 30m)")
    print("==================================================================")

if __name__ == "__main__":
    run_physical_restore_verification()
