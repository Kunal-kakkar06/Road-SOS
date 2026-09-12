# ROAD SOS — SECURITY OPERATIONS & INCIDENT RESPONSE RUNBOOK

## 1. Overview & Purpose
This operational runbook defines emergency procedures, secret rotation workflows, vulnerability management, and incident response protocols for the RoadSOS production infrastructure.

---

## 2. Secrets Management & Rotation Workflow

### Emergency Secret Rotation (`JWT_SECRET` Leak)
If `JWT_SECRET` is compromised or suspected of exposure:
1. Generate a new cryptographically secure 256-bit secret key:
   ```bash
   openssl rand -hex 32
   ```
2. Update `JWT_SECRET` in production configuration store (e.g. AWS Secrets Manager, Kubernetes Secret, or `.env.production`).
3. Trigger a rolling restart of all API Gateway instances:
   ```bash
   docker compose restart api
   ```
4. Revoke existing refresh tokens in PostgreSQL:
   ```sql
   UPDATE refresh_tokens SET is_revoked = TRUE WHERE is_revoked = FALSE;
   ```
5. Notify active client sessions to re-authenticate.

### Database Password Rotation (`DATABASE_URL`)
1. Generate a new database password in PostgreSQL:
   ```sql
   ALTER USER roadsos WITH PASSWORD 'new_secure_password_here';
   ```
2. Update `DATABASE_URL` across API and Worker environment variables:
   ```bash
   DATABASE_URL=postgresql+asyncpg://roadsos:new_secure_password_here@db:5432/roadsos_db
   ```
3. Restart API nodes and ML Workers:
   ```bash
   docker compose restart api worker-1 worker-2
   ```

---

## 3. Incident Response Playbooks

### Incident Scenario A: Authentication Abuse / Token Flooding
* **Detection**: Spikes in `401 Unauthorized` responses in Prometheus metrics (`http_requests_total{status="401"}`).
* **Action**:
  1. Inspect API logs for offending IP addresses:
     ```bash
     docker logs roadsos-api-1 | grep '"status": 401' | awk '{print $NF}' | sort | uniq -c | sort -nr
     ```
  2. Apply rate limiting or IP ban at NGINX / Cloudflare edge layer.
  3. Confirm JWT signature verification remains active.

### Incident Scenario B: IDOR / Cross-Tenant Probing Attempt
* **Detection**: Logs showing repeated 404/403 responses for non-owned UUID lookup attempts.
* **Action**:
  1. Audit request correlation ID to trace user UUID.
  2. Verify DB identity claims: confirm `user_id` on requested resource matches authenticated caller.
  3. Deactivate compromised user account if malicious activity is proven:
     ```sql
     UPDATE users SET is_active = FALSE WHERE uuid = 'offending-user-uuid';
     ```

### Incident Scenario C: Database Denial of Service / Connection Exhaustion
* **Detection**: `DB_POOL_TIMEOUT` warnings in API logs or high PostgreSQL active connection counts.
* **Action**:
  1. Check PostgreSQL active connections:
     ```sql
     SELECT count(*), state FROM pg_stat_activity GROUP BY state;
     ```
  2. Verify connection pool tuning (`DB_POOL_SIZE=20`, `DB_MAX_OVERFLOW=20`).
  3. Terminate idle connection hogs if necessary:
     ```sql
     SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < now() - interval '5 minutes';
     ```

---

## 4. Periodic Security Verification
To maintain production security baseline, run the automated security audit script prior to every deployment release:

```bash
DATABASE_URL=postgresql+asyncpg://roadsos:roadsos_password@localhost:5432/roadsos_db venv/bin/python test_step25_security_audit.py
```

Run full regression tests:
```bash
venv/bin/pytest tests/ -v
```

Run Alembic schema drift verification:
```bash
alembic check
```
