# Step 18 — Production Disaster Recovery, Backup/Restore & Operational Resilience Manual

## 1. Architecture Overview

RoadSOS Step 18 establishes a resilient, production-ready disaster recovery architecture built on PostgreSQL 15, PostGIS, continuous WAL archiving, and snapshot `pg_dump` backups:

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

## 2. PostgreSQL Backup Architecture

### Configuration Environment Variables
```env
BACKUP_ENABLED=true
BACKUP_DIR=/tmp/roadsos_backups
BACKUP_RETENTION_DAYS=7
BACKUP_INTERVAL_HOURS=24
DATABASE_URL=postgresql+asyncpg://roadsos:roadsos_password@localhost:5432/roadsos_db
```

### Backup Execution
Logical snapshot backups are executed via `python scripts/backup_db.py` or `BackupService.create_backup()`:
```bash
python scripts/backup_db.py --outdir /tmp/roadsos_backups
```

- Generates `.sql.gz` compressed snapshot artifact.
- Generates companion `.sha256` checksum manifest.
- Credential masking: Passwords are specified via `PGPASSWORD` and masked in logs (`postgresql://roadsos:****@localhost:5432/roadsos_db`).

---

## 3. Restore Procedure

### Step 3.1: Quiesce Application Write Traffic & Stop Workers
```bash
docker compose stop api worker-1 worker-2
```

### Step 3.2: Verify Backup Checksum Manifest
```bash
LATEST_BACKUP=$(ls -1t /tmp/roadsos_backups/*.sql.gz | head -n 1)
sha256sum -c "${LATEST_BACKUP}.sha256"
```

### Step 3.3: Execute PostgreSQL Restore
```bash
zcat "$LATEST_BACKUP" | docker exec -i backend-db-1 psql -U roadsos -d roadsos_db
```

### Step 3.4: Verify Alembic Migration State
```bash
docker exec backend-api-1 alembic current
docker exec backend-api-1 alembic check
```

### Step 3.5: Restart API & Background Workers
```bash
docker compose start api worker-1 worker-2
```

### Step 3.6: Verify Health Probes
```bash
curl -s http://localhost:8000/api/health | grep '"liveness":true'
curl -s http://localhost:8000/api/ready | grep '"status":"ready"'
```

---

## 4. Operational RPO and RTO Targets

| Target Metric | Target SLA | Implementation Strategy |
| :--- | :--- | :--- |
| **RPO (Recovery Point Objective)** | **24 hours (Logical)** / **≤ 5 min (WAL)** | Scheduled snapshot backups (`backup_db.py`) combined with continuous WAL archiving (`wal_level=replica`, `archive_mode=on`) |
| **RTO (Recovery Time Objective)** | **≤ 1 hour (Target)** | Single-command automated restore runbook and disposable verification (`verify_restore.py`) |

---

## 5. Data Retention Lifecycle

* **`TriageEvent` Audit Records**: Indefinite retention for compliance and auditability. NEVER automatically deleted.
* **Terminal `TriageJob` Queue Records**: Bounded cleanup deletes `completed` or `failed` jobs older than `TRIAGE_JOB_RETENTION_DAYS` (default: 30 days) via `cleanup_old_terminal_jobs()`.
* **Active Jobs**: `pending` and `processing` jobs are strictly protected from cleanup.

---

## 6. Operational Alert Rules

| Alert Name | Condition / Threshold | Recommended Operator Action |
| :--- | :--- | :--- |
| `BackupStale` | `latest_backup_age_seconds > 93600` (26 hours) | Inspect backup cron job or run `python scripts/backup_db.py` manually. |
| `BackupFailure` | `last_backup_success == 0` | Check database credentials and filesystem disk space (`df -h`). |
| `WorkerOutage` | `worker_nodes_active == 0` | Restart worker containers (`docker compose up -d --scale worker=2`). |
| `StaleWorker` | `worker_nodes_stale > 0` | Check worker memory/CPU metrics; surviving workers automatically reclaim stale jobs. |
| `DatabaseFailure` | `/api/ready` returns `503` | Inspect PostgreSQL container health and disk storage. |

---

## 7. Security & Credential Protection

1. **Log Redaction**: Connection string passwords and Bearer JWT tokens are replaced with `[REDACTED_DB_PASS]` / `[REDACTED_TOKEN]`.
2. **Access Control**: Backup output directories (`/tmp/roadsos_backups`) must be restricted with filesystem mode `0700`.
3. **Frontend Isolation**: Backup directories are strictly excluded from web server static file hosting.
