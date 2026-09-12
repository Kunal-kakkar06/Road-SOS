# RoadSOS Step 20 — Operational Alerting Handbook & Runbook

## 1. Overview

This handbook defines Prometheus alerting rules, severity levels, triggers, business impacts, investigation steps, and remediation runbooks for RoadSOS production operations.

---

## 2. Actionable Alert Catalog

### 1. `RoadSOSNoActiveWorkers`
- **Severity**: `CRITICAL`
- **Trigger**: `worker_nodes_active == 0` for 2 minutes
- **Business Impact**: Asynchronous AI triage processing halts; queue depth accumulates.
- **Investigation**: Check worker process logs (`docker logs backend-worker-1`). Inspect `worker_heartbeats` table in database.
- **Remediation**: Restart worker instances: `docker-compose restart worker`.

### 2. `RoadSOSStaleWorkerHeartbeat`
- **Severity**: `WARNING`
- **Trigger**: `worker_nodes_stale > 0` for 3 minutes
- **Business Impact**: A worker node may have hung or crashed.
- **Investigation**: Check node CPU/Memory utilization. Check if worker was killed by OOM killer.
- **Remediation**: Terminate stale container and launch replacement worker instance.

### 3. `RoadSOSHighPendingQueueDepth`
- **Severity**: `WARNING` / `CRITICAL`
- **Trigger**: `triage_jobs_total{status="pending"} > 50` for 5 minutes
- **Business Impact**: Increased triage processing latency for emergency requests.
- **Investigation**: Check average job processing duration and worker CPU allocation.
- **Remediation**: Scale worker replica count: `docker-compose up -d --scale worker=4`.

### 4. `RoadSOSTriageJobHighFailureRate`
- **Severity**: `CRITICAL`
- **Trigger**: `rate(triage_jobs_total{status="failed"}[10m]) > 0.05`
- **Business Impact**: Triage jobs failing to process. Emergency requests encountering fallback.
- **Investigation**: Inspect `triage_events` audit table for exception traces. Verify XGBoost model file availability.
- **Remediation**: Verify database disk space, ML model binary path, and system memory.

### 5. `RoadSOSDatabaseConnectionFailures`
- **Severity**: `CRITICAL`
- **Trigger**: `increase(db_errors_total[5m]) > 5`
- **Business Impact**: API requests failing with 500/503 errors; DB connection pool exhausted.
- **Investigation**: Inspect PostgreSQL connection pool usage, active query counts, and PostgreSQL server logs.
- **Remediation**: Increase SQLAlchemy pool size or restart database container if unresponsive.

### 6. `RoadSOSBackupReplicationFailed`
- **Severity**: `CRITICAL`
- **Trigger**: `disaster_recovery_replication_last_success == 0` for 15 minutes
- **Business Impact**: Local database backups failing to sync to off-site S3 object storage.
- **Investigation**: Inspect `BackupReplicationService` logs for S3 network timeouts or credential errors.
- **Remediation**: Check S3 endpoint connectivity, IAM access keys, and bucket quota.

### 7. `RoadSOSBackupReplicationStale`
- **Severity**: `WARNING`
- **Trigger**: `disaster_recovery_replication_latest_backup_age_seconds > 90000` (25 hours)
- **Business Impact**: Off-site replicated backup artifact is out of date.
- **Investigation**: Check daily snapshot cron job execution log.
- **Remediation**: Trigger manual backup creation: `python backend/scripts/backup_db.py`.
