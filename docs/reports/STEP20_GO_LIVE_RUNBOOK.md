# RoadSOS Step 20 — Production Cutover & Go-Live Runbook

## 1. Pre-Go-Live Readiness Checklist

Execute 1 hour prior to cutover:

- [x] Verify PostgreSQL 15 database is online (`backend-db-1`).
- [x] Verify S3 object storage bucket is online (`roadsos-offsite-backups`).
- [x] Execute pre-deployment logical database backup (`scripts/backup_db.py`).
- [x] Validate SHA-256 backup checksum (`sha256sum -c`).
- [x] Execute disposable restore verification (`scripts/verify_restore.py`).
- [x] Confirm `alembic check` reports zero unmanaged migration drift.
- [x] Confirm environment configuration: `ENVIRONMENT=production`, secure `JWT_SECRET`, PostgreSQL `DATABASE_URL`.

---

## 2. Deployment Execution Protocol

1. **Enable Maintenance Mode**: Point load balancer / ingress to maintenance page if needed.
2. **Execute Database Migrations**:
   ```bash
   alembic upgrade head
   ```
3. **Verify Revision**:
   ```bash
   alembic current
   # Expected Output: a1b2c3d4e5f6 (head)
   ```
4. **Deploy Application Services**:
   ```bash
   docker-compose up -d backend worker
   ```
5. **Verify Application Health**:
   ```bash
   curl -f http://localhost:8000/health
   curl -f http://localhost:8000/api/ready
   ```
6. **Execute Production Smoke Test**:
   ```bash
   pytest tests/ai/test_step20_production_smoke.py -v
   ```

---

## 3. Mandatory Abort & Immediate Rollback Conditions

If any of the following conditions occur during cutover, **STOP IMMEDIATELY AND EXECUTE ROLLBACK**:

1. `alembic upgrade head` fails with a non-zero exit code.
2. `/api/ready` returns HTTP 503 or fails to respond within 30 seconds.
3. Workers fail to claim queued jobs (`worker_nodes_active == 0`).
4. Duplicate `TriageEvent` audit logs detected.
5. Authentication failures or invalid JWT token rejections on valid credentials.
6. XGBoost / NLP triage pipeline returns unexpected predictions or raises exceptions.
7. Critical security regression (PHI/PII leaked in logs or unauthenticated access permitted).

---

## 4. Emergency Rollback Execution Procedure

1. **Stop Application Services**:
   ```bash
   docker-compose stop backend worker
   ```
2. **Revert Migration / Restore Database**:
   - For reversible changes: `alembic downgrade -1`
   - For data/schema changes: Restore pre-deployment backup using `verify_restore.py` into target database.
3. **Re-deploy Previous Application Version**:
   ```bash
   git checkout previous-release-tag
   docker-compose up -d backend worker
   ```
4. **Verify Rollback Readiness**:
   ```bash
   curl -f http://localhost:8000/api/ready
   ```

---

## 5. Post-Go-Live Monitoring (First 24 Hours)

- Monitor Prometheus `/metrics` every 15 minutes:
  - `http_requests_total` failure rate < 0.1%
  - `worker_nodes_active` == active worker count
  - `disaster_recovery_replication_last_success` == 1
  - `db_errors_total` == 0
