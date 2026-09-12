# RoadSOS Production Observability, Monitoring & Alerting Manual

## 1. Architecture Overview

RoadSOS employs a comprehensive, production-grade observability stack designed for emergency medical dispatch and AI triage operations.

```
+-----------------------------------------------------------------------------------+
|                                 ROADSOS SYSTEM                                    |
|                                                                                   |
|  +--------------------+       +--------------------+       +------------------+   |
|  |  FastAPI Backend   | ----> |  PostgreSQL 15 DB  | <---- | Distributed      |   |
|  |  (JSON Logs +      |       |  (Triage Jobs +    |       | Workers (2+)     |   |
|  |   Prometheus Expr) |       |   Heartbeats)      |       | (JSON Logs)      |   |
|  +--------------------+       +--------------------+       +------------------+   |
|           |                                                         |             |
|           v                                                         v             |
|  +-----------------------------------------------------------------------------+  |
|  |                   Correlation Context (X-Request-ID)                        |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
                      +-------------------------------------+
                      |   Prometheus Scraper & Grafana      |
                      |   Alertmanager Monitoring           |
                      +-------------------------------------+
```

---

## 2. Structured JSON Log Schema

All log events emitted by the API and worker processes are formatted as single-line JSON objects to standard stdout/stderr for automated log aggregation (e.g., FluentBit, Grafana Loki, Datadog).

### Field Definitions

| Field Name | Type | Example | Description |
| :--- | :--- | :--- | :--- |
| `timestamp` | string (ISO-8601 UTC) | `"2026-09-10T12:00:00.123456+00:00"` | Precise event timestamp |
| `level` | string | `"INFO"`, `"WARNING"`, `"ERROR"` | Log severity level |
| `service` | string | `"roadsos-api"`, `"roadsos-worker"` | Microservice or container component |
| `environment` | string | `"production"`, `"staging"` | Deployment environment name |
| `event_name` | string | `"api.request.completed"` | Stable machine-readable event identifier |
| `logger` | string | `"roadsos.api"`, `"roadsos.worker"` | Python logger module identifier |
| `request_id` | string (UUID) | `"b9a10d9e-1102-45e0-81f1-a1b2c3d4e5f6"` | Request correlation ID across API & workers |
| `job_id` | string (UUID) | `"job_77a1b2c3d4"` | Triage job identifier |
| `worker_id` | string | `"worker-a1b2c3"` | Distributed worker node identifier |
| `user_id` | string | `"usr_102"` | User ID (if authenticated) |
| `duration_ms` | float | `12.45` | Execution or processing duration in milliseconds |
| `status` | string / int | `"completed"`, `200`, `500` | Operation outcome or HTTP status code |
| `attempt_count` | int | `1` | Job processing attempt count |

### Stable Event Catalog

* `api.request.received` — Incoming HTTP request received
* `api.request.completed` — HTTP request processed successfully
* `api.request.failed` — HTTP request failed with exception
* `triage.job.created` — New triage job submitted to PostgreSQL queue
* `worker.started` — Worker process initialized and connected
* `worker.heartbeat` — Periodic worker heartbeat updated in DB
* `worker.job.claimed` — Job atomically claimed via `FOR UPDATE SKIP LOCKED`
* `worker.job.completed` — Job processed by XGBoost + NLP pipeline
* `worker.job.failed` — Job execution failed (moves to retry or failed state)
* `worker.stopped` — Worker process shut down cleanly
* `database.error` — Database connectivity or transaction failure

---

## 3. End-to-End Request Correlation (`X-Request-ID`)

RoadSOS enforces end-to-end tracing across async job submission and execution:

```
1. Client HTTP Request
   [Header: X-Request-ID: req-12345]
                  │
                  ▼
2. RequestCorrelationMiddleware
   [Validates req-12345, sets ContextVar, logs api.request.received]
                  │
                  ▼
3. Triage API Endpoint
   [Stores TriageJob with request_id = "req-12345"]
                  │
                  ▼
4. Distributed Worker Claim
   [Reads job, binds request_id_var.set("req-12345"), executes ML pipeline]
                  │
                  ▼
5. TriageEvent Audit Log & Response
   [Persists TriageEvent with request_id = "req-12345", returns X-Request-ID in header]
```

If an incoming request lacks `X-Request-ID` or contains invalid characters (e.g. log injection attempt), a clean UUID4 is generated automatically.

---

## 4. Prometheus Metric Catalog (`/metrics`)

The API process exposes Prometheus text format metrics at `/metrics`.

### Metric Catalog Table

| Metric Name | Type | Labels | Description |
| :--- | :--- | :--- | :--- |
| `http_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests processed |
| `triage_jobs_total` | Gauge | `status` | Current count of triage jobs by state (`pending`, `processing`, `completed`, `failed`) |
| `disaster_recovery_oldest_pending_job_age_seconds` | Gauge | None | Age of the oldest pending job in seconds |
| `worker_nodes_active` | Gauge | None | Count of active worker nodes with fresh heartbeats |
| `worker_nodes_stale` | Gauge | None | Count of stale worker nodes (heartbeat > 2 min old) |
| `worker_jobs_processed_total` | Counter | `worker_id`, `status` | Cumulative jobs processed per worker node |
| `db_errors_total` | Counter | None | Total database connection/query failures |
| `disaster_recovery_latest_backup_age_seconds` | Gauge | None | Age of latest verified DB backup in seconds |
| `disaster_recovery_last_backup_success` | Gauge | None | Indicates if the latest backup attempt succeeded (1) or failed (0) |
| `disaster_recovery_backup_size_bytes` | Gauge | None | Size of the latest backup artifact in bytes |
| `disaster_recovery_restore_validation_success` | Gauge | None | Indicates if restore validation succeeded (1) or failed (0) |
| `disaster_recovery_rpo_target_seconds` | Gauge | None | Recovery Point Objective target (300s / 5 min) |
| `disaster_recovery_rto_target_seconds` | Gauge | None | Recovery Time Objective target (900s / 15 min) |

*Label Cardinality Control*: Prometheus labels strictly omit `request_id`, `user_id`, `job_id`, or patient symptom text to avoid high cardinality.

---

## 5. Health & Readiness Separation

RoadSOS separates liveness probing from readiness probing:

### Liveness Probe (`GET /health` or `GET /api/health`)
* **Purpose**: Verifies that the FastAPI process is alive and responding to HTTP calls.
* **DB Dependency**: **NONE**. A temporary database outage will **NOT** cause liveness checks to fail, preventing unnecessary container restarts.
* **HTTP Response**: `200 OK` `{"status": "ok", "service": "RoadSOS API", "liveness": true}`.

### Readiness Probe (`GET /api/ready`)
* **Purpose**: Verifies if the instance can safely receive production traffic.
* **Checks Performed**:
  1. PostgreSQL database connectivity (`SELECT 1`).
  2. Alembic migration head verification.
  3. XGBoost + NLP ML orchestrator model loading verification.
* **HTTP Response**:
  * All healthy: `200 OK` `{"status": "ready", "service": "RoadSOS API", "checks": {...}}`.
  * Dependency down: `503 Service Unavailable` `{"status": "unavailable", "service": "RoadSOS API", "checks": {...}}`.

---

## 6. Alert Definitions

| Alert Name | Severity | Condition / Threshold | Operational Meaning | Recommended Response |
| :--- | :--- | :--- | :--- | :--- |
| `HighHTTP5xxErrorRate` | Critical | Sustained 5xx error rate > 5% for 2 mins | API handling unhandled exceptions or DB crash | Inspect application logs (`event_name="api.request.failed"`); check DB status |
| `OldestPendingJobAgeHigh` | Warning / Critical | Oldest pending job age > 30s (Warning) / > 120s (Critical) | Workers backed up or stuck | Scale worker containers (`docker compose up -d --scale worker=4`); check worker logs |
| `NoActiveWorkers` | Critical | `worker_nodes_active == 0` for 1 min | Worker cluster crashed or down | Restart worker services; inspect worker stack traces |
| `StaleWorkerNode` | Warning | `worker_nodes_stale > 0` | Worker process hung or crashed abruptly | Automated stale job recovery will claim stuck jobs; check worker container resources |
| `DatabaseUnavailable` | Critical | `/api/ready` returns `503` (DB check failed) | PostgreSQL database down or unreachable | Check PostgreSQL container health, disk space, and network connectivity |
| `BackupAgeExceedsRPO` | Critical | `latest_backup_age_seconds > 300` (5 mins) | WAL archiving or cron backup job failing | Run backup script (`python scripts/backup_db.py`); inspect WAL archive storage |
| `BackupFailure` | Critical | `last_backup_success == 0` | Scheduled pg_dump backup execution failed | Check backup script permissions, disk space, and PostgreSQL credentials |
| `RestoreValidationFailure` | Critical | `restore_validation_success == 0` | Backup artifact checksum verification failed | Re-run `python scripts/verify_restore.py`; check disk corruption or file truncation |
| `BackupStorageUnavailable` | Critical | Backup destination directory unwritable | Disk full or permission error on `/tmp/roadsos_backups` | Inspect backup volume mounts and disk usage (`df -h`) |

---

## 7. Log Redaction & Security Policy

To protect patient confidentiality and system security:
1. **Passwords**: Database passwords in connection strings or auth requests are automatically replaced with `[REDACTED_DB_PASS]` / `[REDACTED_SECRET]`.
2. **Tokens**: HTTP `Authorization: Bearer <JWT>` headers and JWT strings are replaced with `[REDACTED_TOKEN]`.
3. **Medical / Patient Data**: Raw patient symptom descriptions (`symptoms`, `text`, `transcript`) are strictly excluded from structured log fields and output as `[REDACTED_SENSITIVE]`.
