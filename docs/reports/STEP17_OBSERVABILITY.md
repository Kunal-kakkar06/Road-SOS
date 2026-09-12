# Step 17 — Production Observability, Monitoring & Operational Readiness Manual

## 1. Executive Summary

RoadSOS Step 17 establishes production-grade observability, request correlation, worker cluster health visibility, application metrics, startup configuration validation, and graceful shutdown handling without altering AI/ML decision logic, XGBoost weights, 10-feature ordering, or API contracts.

---

## 2. Structured Lifecycle Logging

All API and worker events emit machine-readable JSON log objects containing canonical fields:
`timestamp`, `level`, `service`, `environment`, `event_name`, `request_id`, `job_id`, `worker_id`, `user_id`, `processing_mode`, `duration_ms`, `status`, `attempt_count`.

### Triage Lifecycle Event Catalog

* `triage.request.received` — Initial HTTP request received at `/api/triage/jobs`.
* `triage.job.created` — Job successfully stored in PostgreSQL `triage_jobs` queue.
* `triage.job.claimed` — Distributed worker atomically claimed job via `FOR UPDATE SKIP LOCKED`.
* `triage.processing.started` — XGBoost + NLP inference pipeline initialized.
* `triage.processing.completed` — ML pipeline executed successfully and severity score computed.
* `triage.processing.failed` — Exception encountered during job execution.
* `triage.job.retried` — Job reset to `pending` status for retry (attempts < 3).
* `triage.job.recovered` — Stale processing job reclaimed by surviving worker after heartbeat timeout.
* `triage.job.finalized` — Job reaches terminal `completed` or `failed` state and `TriageEvent` audit log is written.

---

## 3. Correlation & Request Tracing

RoadSOS propagates `request_id` across the complete async lifecycle:

```
HTTP Request (Header: X-Request-ID) 
  ──► RequestCorrelationMiddleware (Sets ContextVar, generates UUID if missing)
  ──► Triage API Router (Stores request_id in triage_jobs table)
  ──► Distributed Worker (Binds request_id to worker execution context)
  ──► ML Pipeline Execution
  ──► TriageEvent Audit Entry (Persists request_id in database)
  ──► HTTP Response Header (X-Request-ID: <request_id>)
```

---

## 4. Worker Cluster Health Visibility

RoadSOS provides operational visibility into active worker cluster nodes without exposing patient medical data:

### Endpoint: `GET /api/ai/worker-health`

Example Response:
```json
{
  "status": "healthy",
  "app_version": "step17",
  "active_worker_count": 2,
  "workers": [
    {
      "worker_id": "worker-a1b2c3d4",
      "last_heartbeat": "2026-09-10T12:00:00+00:00",
      "status": "active",
      "job_id": null,
      "completed_jobs": 15,
      "failed_jobs": 0
    },
    {
      "worker_id": "worker-e5f6g7h8",
      "last_heartbeat": "2026-09-10T12:00:01+00:00",
      "status": "active",
      "job_id": "job_99a1b2",
      "completed_jobs": 12,
      "failed_jobs": 0
    }
  ]
}
```

---

## 5. Application Health & Configuration Validation

### Application Versioning (`APP_VERSION`)
The application version (default `step17`) is exposed in:
* `GET /health`
* `GET /api/health`
* `GET /api/ready`
* `GET /api/ai/health`
* `GET /api/ai/worker-health`
* Structured JSON startup log lines.

### Startup Configuration Validation
On application load, `validate_production_configuration()` inspects environment variables:
* In `production` environment (`ENVIRONMENT=production`):
  * Rejects SQLite database connections (requires PostgreSQL).
  * Rejects missing or default `JWT_SECRET` keys.
  * Fails fast with `ValueError` to prevent unsafe startup.

---

## 6. Graceful Shutdown & Database Pool Safety

* **API Shutdown**: Listens for `SIGTERM`/`SIGINT`. Disposes SQLAlchemy async engine connections cleanly (`await engine.dispose()`).
* **Worker Shutdown**: Registers signal handlers, stops claiming new jobs, emits `worker.stopped` event, updates worker status in `worker_heartbeats` to `stopping`, and cleanly releases database sessions.

---

## 7. Operational Alert Conditions

| Alert Name | Condition / Threshold | Recommended Operator Action |
| :--- | :--- | :--- |
| `StaleWorkerNode` | `last_heartbeat > 2 minutes` | Check worker container CPU/memory usage; stale jobs are auto-reclaimed. |
| `NoActiveWorkers` | `active_worker_count == 0` for 1 min | Scale worker containers (`docker compose up -d --scale worker=2`). |
| `DatabaseUnavailable` | `/api/ready` returns `503` | Inspect PostgreSQL container health and network connectivity. |
| `HighJobFailureRate` | `failed_jobs > 5%` over 5 minutes | Inspect worker logs for `triage.processing.failed` exception traces. |
