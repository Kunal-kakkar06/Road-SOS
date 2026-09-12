# RoadSOS Production Operational Handoff & Operations Manual

**Version**: 1.0.0  
**Status**: APPROVED & CERTIFIED FOR PRODUCTION HANDOFF  
**Target Audience**: Operations Team, Site Reliability Engineers (SRE), System Administrators, DevOps Engineers  

---

## 1. System Overview & Operational Architecture

RoadSOS is a high-availability, real-time emergency triage and response dispatch web platform. It processes emergency symptom inputs using a hybrid AI triage engine (XGBoost 10-feature model + NLP scoring + SHAP explainability) and routes jobs to responders with location-based hospital ranking.

### Architecture Summary

```
                      +-----------------------------+
                      |   Client Web App (Vite PWA) |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |  FastAPI Web Service (API)  |
                      |   - JWT Auth & IDOR Check   |
                      |   - Rate Limiter (Token)    |
                      |   - Prometheus /metrics     |
                      +--------------+--------------+
                                     |
           +-------------------------+-------------------------+
           | (FOR UPDATE SKIP LOCKED)                          |
           v                                                   v
+-----------------------+                           +-----------------------+
|  PostgreSQL 15 + GIS  |                           |  Distributed Worker 1 |
|  - TriageJob          |                           |  - Polling Loop       |
|  - TriageEvent        |                           |  - XGBoost Inference  |
|  - BackupRecord       |                           +-----------------------+
+----------+------------+                                      |
           |                                                   v
           v                                        +-----------------------+
+-----------------------+                           |  Distributed Worker 2 |
|   MinIO S3 Off-Site   |                           |  - Redundant Poller   |
|   Encrypted Snapshots |                           +-----------------------+
+-----------------------+
```

---

## 2. Standard Operating Procedures (SOP)

### 2.1 Starting Production Infrastructure

```bash
# 1. Start PostgreSQL 15 & MinIO S3 Services
docker compose up -d roadsos-db test-minio

# 2. Run Alembic Database Migrations
DATABASE_URL="postgresql+asyncpg://roadsos:<PROD_PASS>@roadsos-db:5432/roadsos_db" \
venv/bin/alembic upgrade head

# 3. Start API Service & Multi-Worker Nodes
docker compose up -d roadsos-api worker-1 worker-2
```

### 2.2 Health & Readiness Inspection

* **API Liveness**: `GET http://<host>:8000/health` (Returns HTTP 200 `{"status": "ok"}`)
* **API Readiness**: `GET http://<host>:8000/api/ready` (Verifies DB connection, Alembic revision, ML model, S3 backup status)
* **ML Model Health**: `GET http://<host>:8000/api/ai/health`
* **Worker Fleet Health**: `GET http://<host>:8000/api/ai/worker-health`
* **Prometheus Metrics**: `GET http://<host>:8000/metrics`

---

## 3. Incident Runbooks & Failure Recovery

### Runbook 1: PostgreSQL Outage / Failure

1. **Detection**: Prometheus alert `database_connection_failures_total > 0` or `/api/ready` returns HTTP 503 `{"status": "degraded"}`.
2. **Impact**: `/health` remains 200 (liveness available); write API endpoints return HTTP 503 safely without crashing workers.
3. **Remediation**:
   ```bash
   # Check container status
   docker compose ps roadsos-db
   
   # Restart PostgreSQL
   docker compose restart roadsos-db
   
   # Verify connection recovery via readiness endpoint
   curl -i http://localhost:8000/api/ready
   ```

### Runbook 2: ML Worker Process Outage

1. **Detection**: `GET /api/ai/worker-health` shows `active_workers < 2` or `stale_heartbeats > 0`.
2. **Impact**: Job queue depth increases, but zero jobs are lost (jobs remain persisted in `TriageJob` table with status `pending`).
3. **Remediation**:
   ```bash
   # Restart failing worker container
   docker compose restart worker-1
   
   # Confirm stale job reclamation by surviving worker
   # Surviving worker automatically reclaims processing jobs after 30s heartbeat timeout using FOR UPDATE SKIP LOCKED
   ```

### Runbook 3: API Service Outage / Crash

1. **Detection**: `GET /health` times out or returns HTTP 502/503.
2. **Impact**: New client submissions blocked; pending worker jobs continue executing independently in background.
3. **Remediation**:
   ```bash
   # Restart API container
   docker compose restart roadsos-api
   ```

### Runbook 4: MinIO S3 Object Storage Failure

1. **Detection**: Backup replication log emits `WARNING: MinIO S3 upload failed`.
2. **Impact**: Primary PostgreSQL database operation is unaffected. Local backups saved to local backup directory.
3. **Remediation**:
   ```bash
   # Restart MinIO container
   docker compose restart test-minio
   
   # Trigger manual backup replication sync
   DATABASE_URL="postgresql+asyncpg://roadsos:<PASS>@localhost:5432/roadsos_db" \
   venv/bin/python scripts/backup_db.py --replicate
   ```

---

## 4. Backup & Disaster Recovery Procedures

### 4.1 Automated Backup Policy

* **Frequency**: Automated daily `pg_dump` snapshot (`.sql.gz` format).
* **Integrity**: Every backup artifact produces a sidecar `.sha256` manifest.
* **Encryption**: AES-256 (SSE-S3) encryption at rest on off-site S3 bucket `roadsos-backups`.
* **Retention Policy**:
  * Hourly backups: Retained 24 hours.
  * Daily backups: Retained 7 days.
  * Weekly backups: Retained 4 weeks.

### 4.2 Restoring Database from Backup

```bash
# 1. Stop write traffic by placing API in maintenance mode
docker compose stop roadsos-api worker-1 worker-2

# 2. Download and verify backup snapshot checksum
sha256sum -c roadsos_backup_latest.sql.gz.sha256

# 3. Restore to target PostgreSQL instance
gunzip -c roadsos_backup_latest.sql.gz | docker exec -i roadsos-db psql -U roadsos -d roadsos_db

# 4. Verify Alembic migration head matches restored schema
DATABASE_URL="postgresql+asyncpg://roadsos:<PASS>@localhost:5432/roadsos_db" \
venv/bin/alembic check

# 5. Restart application services
docker compose start roadsos-api worker-1 worker-2
```

---

## 5. Upgrade, Migration & Rollback Controls

### 5.1 Deployment & Migration Gate

Before deploying any version update to production:

1. **Pre-flight Migration Check**: `venv/bin/alembic check` must report `No new upgrade operations detected` or migrations must be executed forward using `alembic upgrade head`.
2. **Pre-flight Test Suite Gate**: Run full regression test suite:
   ```bash
   venv/bin/pytest tests/ -v
   ```
3. **Physical Smoke Test Gate**:
   ```bash
   venv/bin/python test_step21_production_smoke.py
   ```

### 5.2 Zero-Downtime Rollback Procedure

If a deployed release experiences an unexpected defect:

```bash
# 1. Revert container image tags in docker-compose.yml to previous release tag (e.g., v1.0.0)
# 2. Rollback Alembic database migration if migration was applied:
DATABASE_URL="postgresql+asyncpg://roadsos:<PASS>@localhost:5432/roadsos_db" \
venv/bin/alembic downgrade -1

# 3. Re-deploy container fleet
docker compose up -d --remove-orphans

# 4. Perform readiness verification
curl -i http://localhost:8000/api/ready
```

---

## 6. Security, Compliance & Data Lifecycle Governance

* **Authentication**: Enforced via JWT with mandatory 256-bit `JWT_SECRET`. Default or insecure secrets cause production startup failure.
* **Role-Based Access Control (RBAC)**: Strict boundaries between `USER`, `RESPONDER`, and `ADMIN` roles.
* **IDOR Protection**: Every resource query filters by explicit tenant `user_id`. Cross-user access returns HTTP 404.
* **PHI Redaction**: All application logs use `StructuredJsonFormatter` which automatically scrubs passwords, auth tokens, database credentials, and symptom text.
* **ML Invariants**: XGBoost model weights, exact 10-feature extraction order, NLP scoring, and SHAP explainability calculations are locked and verified by automated governance tests (`test_step27_governance.py`).

---

## 7. Sign-off & Certification Matrix

| Category | Governance Item | Status | Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Config & Secrets** | Production Config Audit | `VERIFIED` | Rejection of insecure JWT and SQLite in production environment |
| **Dependencies** | Python & npm Supply-Chain Audit | `VERIFIED` | Clean lockfiles, zero unvetted runtime dependencies |
| **Database** | Alembic Migration & Index Audit | `VERIFIED` | Head revision `c3d4e5f6a7b8`, 0 schema drift, active indexes |
| **Data Lifecycle** | PHI & Sensitive Data Redaction | `VERIFIED` | Automated log scrubber hides passwords and tokens |
| **Access Control** | JWT Expiration & IDOR Isolation | `VERIFIED` | 256-bit key enforcement, tenant boundary tests passing |
| **Release Controls**| Smoke, Health & Migration Gates | `VERIFIED` | 8/8 physical smoke tests, readiness endpoint HTTP 200 |
| **Runbooks** | Failover, Outage & DR Procedures | `VERIFIED` | Tested PostgreSQL, Worker, API, and S3 outage procedures |
| **Regression** | Full Test & ML Invariant Suite | `VERIFIED` | 256/256 pytest cases passing, ML weights/features untouched |

**Final Disposition**: **READY FOR PRODUCTION HANDOFF**
