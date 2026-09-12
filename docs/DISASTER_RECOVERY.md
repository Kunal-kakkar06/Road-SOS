# RoadSOS Production Disaster Recovery & Data Durability Manual

## 1. Architecture Overview

RoadSOS guarantees high availability, data durability, and rapid disaster recovery for emergency medical dispatch operations through a multi-tiered backup and recovery architecture:

```
+------------------------------------------------------------------------------------+
|                               PRIMARY DATASTORE                                    |
|                                                                                    |
|  +------------------------------------------------------------------------------+  |
|  |                PostgreSQL 15 Datastore (roadsos_db)                          |  |
|  |  - users, triage_events, triage_jobs, worker_heartbeats, hospitals          |  |
|  +------------------------------------------------------------------------------+  |
|         │                                                          │               |
|         │ Continuous WAL Archiving                                 │ Base Backup   |
|         ▼ (archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f') ▼ (pg_dump)|
|  +-----------------------------+                           +---------------------+ |
|  | WAL Archive Storage         |                           | Snapshot Storage    | |
|  | (RPO <= 5 minutes)          |                           | (/tmp/roadsos_backups)|
|  +-----------------------------+                           +---------------------+ |
|                                                                    │               |
|                                                                    ▼               |
|                                                           +---------------------+ |
|                                                           | SHA-256 Checksum    | |
|                                                           | Verification        | |
|                                                           +---------------------+ |
+------------------------------------------------------------------------------------+
```

---

## 2. RPO and RTO SLA Definitions

| Metric | Target SLA | Implementation Strategy | Verification Method |
| :--- | :--- | :--- | :--- |
| **RPO (Recovery Point Objective)** | **≤ 5 minutes** | Base PostgreSQL snapshot backups + Continuous WAL Archiving (`wal_level=replica`, `archive_mode=on`) | Continuous WAL segment archiving and backup age metric monitoring (`disaster_recovery_latest_backup_age_seconds`) |
| **RTO (Recovery Time Objective)** | **≤ 15 minutes** | Automated backup verification and deterministic single-command restore runbook | Measured restore execution time during live DR verification suite (`test_step20_live_verification.py`) |

---

## 3. Backup Architecture & Strategy

1. **Snapshot Backups (`scripts/backup_db.py`)**:
   - Executes automated `pg_dump` with `--clean --if-exists --no-owner --no-privileges`.
   - Generates timestamped `.sql.gz` artifacts in `/tmp/roadsos_backups/`.
   - Computes SHA-256 hash and writes companion `.sha256` checksum manifest.
   - Strictly masks connection credentials and passwords from standard output.
2. **Retention Lifecycle (`scripts/cleanup_backups.py`)**:
   - Maintains rolling window of backup artifacts.
   - Cleans up backups older than configured retention period (default: 7 days).

---

## 4. Automated Backup Verification & Restore Probing

RoadSOS validates backup integrity before emergency recovery is needed:

1. **Existence & Size Check**: Confirms `.sql.gz` artifact exists and is non-empty (>0 bytes).
2. **SHA-256 Checksum Validation**: Recalculates artifact hash and matches against stored `.sha256` manifest.
3. **Disposable Restore Probing (`scripts/verify_restore.py`)**: Restores backup artifact into an isolated temporary database (`roadsos_restore_verify_tmp`), validating schema structure, row counts, and indexes without touching production data.
4. **Point-In-Time Recovery (PITR) Validation (`scripts/verify_pitr.py`)**: Verifies WAL segment replay consistency.

---

## 5. Step-by-Step Emergency Restore Runbook

In the event of database failure or corrupted state, follow this deterministic recovery sequence:

### Step 5.1: Quiesce Traffic & Stop Workers
```bash
# Stop application API write traffic and background workers
docker compose stop api worker-1 worker-2
```

### Step 5.2: Locate Latest Verified Backup & Verify SHA-256 Checksum
```bash
LATEST_BACKUP=$(ls -1t /tmp/roadsos_backups/roadsos_backup_*.sql.gz | head -n 1)
echo "Latest Backup Artifact: $LATEST_BACKUP"

# Validate SHA-256 checksum
sha256sum -c "${LATEST_BACKUP}.sha256"
```

### Step 5.3: Execute Database Restore
```bash
# Decompress and restore into PostgreSQL
zcat "$LATEST_BACKUP" | docker exec -i backend-db-1 psql -U roadsos -d roadsos_db
```

### Step 5.4: Execute Schema & Migration Safety Checks
```bash
# Verify Alembic migration state
docker exec backend-api-1 alembic current
docker exec backend-api-1 alembic check
```

### Step 5.5: Validate Database Table Integrity & Row Counts
```bash
docker exec -i backend-db-1 psql -U roadsos -d roadsos_db -c "
SELECT 'users' AS table_name, COUNT(*) FROM users
UNION ALL
SELECT 'triage_jobs', COUNT(*) FROM triage_jobs
UNION ALL
SELECT 'triage_events', COUNT(*) FROM triage_events
UNION ALL
SELECT 'worker_heartbeats', COUNT(*) FROM worker_heartbeats;
"
```

### Step 5.6: Restart API & Background Workers
```bash
docker compose start api worker-1 worker-2
```

### Step 5.7: Verify Liveness & Readiness Probes
```bash
curl -s http://localhost:8000/api/health | grep '"liveness":true'
curl -s http://localhost:8000/api/ready | grep '"status":"ready"'
```

---

## 6. Data Integrity & Ownership Isolation

Disaster recovery procedures guarantee data integrity across all core tables:
* **Foreign Keys**: Cascading constraints between `users`, `triage_jobs`, `triage_events`, and `worker_heartbeats` are preserved intact.
* **IDOR Protection**: Restoring datastore state does **NOT** alter user ownership boundaries (`user_id` context filtering remains strictly enforced).
* **Idempotency**: Duplicate event prevention prevents re-insertion of existing `TriageEvent` records upon worker queue resumption.

---

## 7. Security & Encryption-at-Rest Requirements

1. **Credential Protection**: Passwords and secrets are injected via environment variables (`POSTGRES_PASSWORD`, `DATABASE_URL`). Connection credentials are NEVER written to backup files or stdout.
2. **Access Control**: Backup output directories (`/tmp/roadsos_backups`) must be restricted with filesystem permissions `0700` (`chmod 700 /tmp/roadsos_backups`).
3. **Frontend Isolation**: Backup directories are strictly excluded from web server static file hosting.
4. **Cloud Encryption-at-Rest**: Production cloud deployments (AWS S3 / GCP Storage) must enforce Server-Side Encryption (`AES-256` or `aws:kms`) on backup storage buckets.
