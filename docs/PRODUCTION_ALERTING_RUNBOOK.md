# RoadSOS Production Alerting & Operational Runbook

**Target Infrastructure**: RoadSOS Live Production Stack (API, PostgreSQL 15, ML Worker Fleet, MinIO S3)  
**Alerting System**: Prometheus + Alertmanager  
**Dashboard Target**: Grafana Operational Dashboard (`backend/grafana_dashboard.json`)  
**Effective Date**: September 11, 2026  

---

## Executive Overview

This operational runbook details every production Prometheus alert configured in `backend/prometheus_alerts.yml`. Operators and on-call engineers must follow the diagnostic and remediation procedures below when an alert triggers.

---

## Production Alert Runbooks

### 1. `RoadSOS_API_Outage`
- **Severity**: `critical`
- **Trigger**: `up{job="roadsos-api"} == 0` for 1 minute
- **Impact**: Complete API unavailability. Emergency triage requests rejected.
- **Diagnostic Steps**:
  1. Check Docker container status: `docker compose ps`
  2. Inspect API logs: `docker compose logs api --tail=100`
  3. Verify PostgreSQL connectivity: `pg_isready -h localhost -p 5432 -U roadsos`
- **Remediation**:
  1. Restart API instance: `docker compose restart api`
  2. If database connection error, restart DB pool: `docker compose restart db api`

---

### 2. `RoadSOS_Readiness_Failed`
- **Severity**: `critical`
- **Trigger**: `/api/ready` returns non-200 or `roadsos_api_ready_status == 0` for 30s
- **Impact**: API instance marked unready by load balancer. Traffic diverted or dropped.
- **Diagnostic Steps**:
  1. Curl readiness endpoint: `curl -v http://localhost:8000/api/ready`
  2. Check probe failure reasons (e.g. `database`, `alembic`, `ml_pipeline`).
- **Remediation**:
  1. If DB failure: verify PostgreSQL process health & disk space.
  2. If ML failure: verify `models/fusion_triage.pkl` permissions and path.

---

### 3. `RoadSOS_WorkerFleetDegraded`
- **Severity**: `warning`
- **Trigger**: `worker_nodes_active < 2` for 2 minutes
- **Impact**: Async job queue throughput reduced. Potential processing delay.
- **Diagnostic Steps**:
  1. Check worker container status: `docker compose ps`
  2. Inspect worker heartbeats: `SELECT * FROM worker_heartbeats WHERE status = 'active'`
- **Remediation**:
  1. Scale worker containers: `docker compose up -d --scale worker-1=1 --scale worker-2=1`
  2. Inspect failed worker logs: `docker compose logs worker-1 --tail=100`

---

### 4. `RoadSOS_QueueBuildup`
- **Severity**: `warning`
- **Trigger**: `triage_jobs_total{status="pending"} > 20` for 3 minutes
- **Impact**: High queue depth. Async job completion latency SLA at risk (>2s).
- **Diagnostic Steps**:
  1. Check worker processing rate: `SELECT count(*) FROM triage_jobs WHERE status = 'processing'`
  2. Check for locked transactions or long-running queries in PostgreSQL.
- **Remediation**:
  1. Verify worker heartbeats. Restart stalled worker processes.
  2. Spawn additional worker instances if traffic spike occurs.

---

### 5. `RoadSOS_OldestPendingJobStale`
- **Severity**: `critical`
- **Trigger**: `disaster_recovery_oldest_pending_job_age_seconds > 60` for 1 minute
- **Impact**: Triage job SLA breach (>60s pending). Patient assistance delayed.
- **Diagnostic Steps**:
  1. Query oldest pending job: `SELECT * FROM triage_jobs WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1`
  2. Verify `FOR UPDATE SKIP LOCKED` worker claims in `worker.py`.
- **Remediation**:
  1. Force stale job status reset if worker crashed mid-transaction.
  2. Ensure worker processes are running and active.

---

### 6. `RoadSOS_PostgreSQL_ConnectionFailure`
- **Severity**: `critical`
- **Trigger**: `increase(database_connection_failures_total[5m]) > 0`
- **Impact**: Database query failures. API & workers unable to persist state.
- **Diagnostic Steps**:
  1. Check PostgreSQL container health: `docker inspect backend-db-1`
  2. Check connection count: `SELECT count(*) FROM pg_stat_activity`
- **Remediation**:
  1. Verify connection pool settings (`pool_pre_ping=True` handles transient drops).
  2. Increase `max_connections` if connection pool is exhausted.

---

### 7. `RoadSOS_Backup_RPO_Violation`
- **Severity**: `warning`
- **Trigger**: `disaster_recovery_latest_backup_age_seconds > 300` for 5 minutes
- **Impact**: Recovery Point Objective (RPO) target breached (>5 minutes). Data loss risk in disaster.
- **Diagnostic Steps**:
  1. Check backup directory `/tmp/roadsos_backups/` for recent `.sql.gz` files.
  2. Check MinIO S3 object replication log: `docker compose logs api`
- **Remediation**:
  1. Manually trigger database backup service: `python -m services.backup_service`
  2. Verify MinIO S3 credentials and endpoint reachability.

---

### 8. `RoadSOS_ElevatedErrorRate`
- **Severity**: `critical`
- **Trigger**: `5xx_rate / total_rate > 0.01` (1%) over 5 minutes
- **Impact**: Server-side error spike impacting users.
- **Diagnostic Steps**:
  1. Filter API logs for HTTP 500 status codes.
  2. Trace request using `X-Request-ID` correlation log entry.
- **Remediation**:
  1. Roll back recent application code deployment if defect detected.
  2. Restart API services.
