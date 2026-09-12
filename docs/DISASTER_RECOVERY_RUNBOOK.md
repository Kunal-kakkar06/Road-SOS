# RoadSOS Disaster Recovery & Operational Restore Runbook

## Overview
This runbook provides step-by-step instructions for operators to recover the RoadSOS system from database corruption, node loss, or storage outages.

---

## Operational Recovery Procedures

### Step 1: Detect Incident & Declare Outage
- Identify failure via Prometheus alerts (`ApiReadinessFailure`, `DatabaseConnectionExhaustion`, `WorkerClusterDown`) or non-200 responses on `/api/ready`.
- Notify emergency response team and set incident severity (P1/P2).

### Step 2: Stop Affected Services
- Stop API and worker containers to prevent partial database writes during recovery:
  ```bash
  docker compose stop api worker-1 worker-2
  ```

### Step 3: Preserve Evidence & Audit Logs
- Export container logs and database system logs to external storage:
  ```bash
  docker logs backend-api-1 > /var/log/roadsos/incident_$(date +%Y%m%d_%H%M%S)_api.log
  docker logs backend-worker-1 > /var/log/roadsos/incident_$(date +%Y%m%d_%H%M%S)_worker.log
  ```

### Step 4: Identify Latest Valid Backup
- Locate the most recent valid backup file locally or from off-site S3 storage bucket `roadsos-backups`:
  ```bash
  # Local
  ls -la /tmp/roadsos_backups/roadsos_backup_*.sql.gz | tail -n 1
  ```

### Step 5: Verify SHA-256 Checksum & Companion Metadata
- Validate SHA-256 digest before initiating restore:
  ```bash
  sha256sum -c /tmp/roadsos_backups/roadsos_backup_roadsos_db_XXXXXX.sql.gz.sha256
  cat /tmp/roadsos_backups/roadsos_backup_roadsos_db_XXXXXX.sql.gz.json
  ```

### Step 6: Provision Replacement PostgreSQL Environment
- If primary PostgreSQL container is corrupted, recreate container or provision new PostgreSQL 15 instance:
  ```bash
  docker compose down -v db
  docker compose up -d db
  ```

### Step 7: Restore Database Snapshot
- Execute isolated database restore verification:
  ```bash
  DATABASE_URL=postgresql+asyncpg://roadsos:roadsos_password@localhost:5432/roadsos_db python backend/test_step23_restore.py
  ```
- Or restore manually using containerized `psql`:
  ```bash
  gunzip -c /tmp/roadsos_backups/roadsos_backup_XXXX.sql.gz | docker exec -i backend-db-1 psql -U roadsos -d roadsos_db
  ```

### Step 8: Verify Schema & Table Integrity
- Query core table schemas to confirm indices, foreign keys, and primary keys exist:
  ```sql
  SELECT table_name FROM information_schema.tables WHERE table_schema='public';
  ```

### Step 9: Verify Row Counts
- Verify critical table row counts match expected baseline:
  - `users`
  - `triage_jobs`
  - `triage_events`
  - `incidents`
  - `hospitals`
  - `providers`
  - `alembic_version`

### Step 10: Run Alembic Migration Validation
- Ensure database schema matches target migration revision (`c3d4e5f6a7b8`):
  ```bash
  alembic check && alembic current
  ```

### Step 11: Start API Containers
- Start the API service:
  ```bash
  docker compose up -d api
  ```

### Step 12: Start Worker Cluster
- Start the worker instances:
  ```bash
  docker compose up -d worker-1 worker-2
  ```

### Step 13: Verify Liveness & Readiness Probes
- Execute health probe checks:
  ```bash
  curl -s http://localhost:8000/health | jq
  curl -s http://localhost:8000/api/ready | jq
  ```

### Step 14: Verify Worker Cluster Health
- Confirm active worker heartbeats:
  ```bash
  curl -s http://localhost:8000/api/ai/worker-health | jq
  ```

### Step 15: Verify Triage History Integrity
- Authenticate a test user session and query `/api/triage/history` to confirm historical records remain readable.

### Step 16: Verify Async Triage Job Processing
- Submit a new test asynchronous triage request:
  ```bash
  curl -X POST http://localhost:8000/api/triage/async \
    -H "Authorization: Bearer <TEST_TOKEN>" \
    -H "Content-Type: application/json" \
    -d '{"text": "Disaster recovery verification request"}'
  ```

### Step 17: Re-Enable Production Traffic
- Once `/api/ready` returns `HTTP 200 OK` with `status: ready`, re-enable ingress routing at NGINX / Cloudflare edge.

---

## Stale Worker Reclamation & Component Failure Resilience (Tested in Step 26)

### Step 19: Stale Worker Crash Recovery Procedure
- **Trigger**: Worker node terminates unexpectedly (`SIGKILL` or node crash) while processing active jobs.
- **Automated Behavior**:
  1. Crashed worker's heartbeat stops (`last_heartbeat` exceeds 5-minute `WORKER_STALE_TIMEOUT_MINUTES`).
  2. Live worker (`worker-2`) executes PostgreSQL `FOR UPDATE SKIP LOCKED` query.
  3. Job is atomically reclaimed by `worker-2`, updating `worker_id` and resetting `heartbeat_at`.
  4. Attempt count increments (`attempt_count + 1`). If `attempt_count >= 3`, job transitions to `failed` and emits alert `worker.job.failed`.
- **Manual Verification**:
  ```sql
  -- Inspect stale or orphaned jobs in PostgreSQL
  SELECT id, worker_id, status, attempt_count, heartbeat_at 
  FROM triage_jobs 
  WHERE status = 'processing' AND heartbeat_at < NOW() - INTERVAL '5 minutes';
  ```

### Step 20: Database Outage Readiness Isolation Procedure
- **Trigger**: PostgreSQL becomes unreachable.
- **Automated Behavior**:
  1. `/api/health` (Liveness) remains `HTTP 200 OK` (`liveness: true`).
  2. `/api/ready` (Readiness) fails `SELECT 1` probe and immediately returns `HTTP 503 Service Unavailable` (`status: unavailable`), causing Kubernetes / ALB to pull node out of load balancer rotation.
  3. API requests return generic `HTTP 503` detail messages without leaking stack traces or connection strings.
  4. Upon PostgreSQL restoration, `pool_pre_ping=True` automatically recovers connection pool.
  5. `/api/ready` returns `HTTP 200 OK` (`status: ready`), automatically re-enabling traffic flow.

### Step 18: Record Incident & Conduct Post-Mortem
- Document RPO (time elapsed between latest backup and outage) and RTO (total downtime until traffic re-enabled).

---

## Rollback & Abort Conditions
- If the restored database fails row count audit or Alembic check, abort container restart, preserve current database state, and attempt restore from the prior daily backup snapshot (`roadsos_backup_*.sql.gz`).
