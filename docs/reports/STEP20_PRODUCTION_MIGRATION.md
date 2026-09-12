# RoadSOS Step 20 — Production Schema Migration Plan

## 1. Overview

This document defines the production database migration lifecycle for RoadSOS, covering pre-deployment database verification, migration execution, readiness validation, and explicit rollback classification.

---

## 2. Pre-Deployment Protocol

Before executing schema migrations on the production PostgreSQL database:

1. **Logical Backup**: Create a full `pg_dump` snapshot using `scripts/backup_db.py`:
   ```bash
   python backend/scripts/backup_db.py --outdir /var/backups/roadsos
   ```
2. **SHA-256 Checksum Validation**: Verify backup file integrity:
   ```bash
   sha256sum -c /var/backups/roadsos/roadsos_backup_*.sql.gz.sha256
   ```
3. **Disposable Restore Test**: Verify the backup snapshot restores cleanly:
   ```bash
   python backend/scripts/verify_restore.py --backup-file /var/backups/roadsos/roadsos_backup_*.sql.gz
   ```
4. **Current Alembic Revision Audit**: Record the active database migration revision:
   ```bash
   alembic current
   ```
5. **Target Alembic Revision Check**: Confirm the target revision (`a1b2c3d4e5f6`):
   ```bash
   alembic heads
   ```
6. **Schema Drift Audit**: Confirm no unmanaged DDL drift exists:
   ```bash
   alembic check
   ```

---

## 3. Deployment Migration Execution

1. Set application into maintenance readiness mode (`/api/ready` returns HTTP 530 / Maintenance if enabled).
2. Execute Alembic schema upgrades:
   ```bash
   alembic upgrade head
   ```
3. Verify target revision:
   ```bash
   alembic current
   # Expected Output: a1b2c3d4e5f6 (head)
   ```
4. Verify table structures, constraints, and PostGIS indexes:
   - `users`
   - `triage_jobs`
   - `triage_events`
   - `incidents`
   - `hospitals`
   - `providers`
   - `worker_heartbeats`
5. Launch FastAPI application server and background worker processes:
   ```bash
   docker-compose up -d backend worker
   ```
6. Verify `/api/ready` readiness probe (`HTTP 200 OK`).

---

## 4. Rollback Classification & Procedures

Not all migrations can be safely reversed via `alembic downgrade`. RoadSOS explicitly classifies migration rollbacks:

| Migration Type | Downgrade Safety | Recommended Rollback Strategy |
| :--- | :--- | :--- |
| **Additive Schema Changes** (New tables, new optional columns, new indexes) | **Safe for Downgrade** | `alembic downgrade -1` $\rightarrow$ Restart application |
| **Destructive Schema Changes** (Column deletion, type narrowing, constraint tightening) | **Unsafe for Downgrade** | **Full Database Backup Restore** from pre-deployment snapshot |
| **Data Transformations** (Column splits, hashing, data backfills) | **Unsafe for Downgrade** | **Full Database Backup Restore** from pre-deployment snapshot |

### Procedure for Reversible Migrations:
```bash
docker-compose stop backend worker
alembic downgrade -1
docker-compose up -d backend worker
```

### Procedure for Unsafe Migrations (Database Backup Restore):
```bash
docker-compose stop backend worker
python backend/scripts/verify_restore.py --backup-file /var/backups/roadsos/pre_deploy_backup.sql.gz
psql -h localhost -U roadsos -d roadsos_db -f /tmp/roadsos_restore_verify_tmp/dump.sql
alembic stamp pre_deployment_revision
docker-compose up -d backend worker
```
