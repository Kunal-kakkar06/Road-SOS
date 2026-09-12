# RoadSOS Secret & Certificate Rotation Runbook

**Runbook Version**: v1.0.0  
**Target Scope**: `JWT_SECRET`, Database credentials (`DATABASE_URL`), MinIO credentials (`MINIO_SECRET_KEY`), TLS certificates

---

## 1. Secret Rotation Lifecycle SOP

The rotation lifecycle follows a strict 6-stage validation sequence:

```
[Old Secret Active] → [Rotation Prep] → [New Secret Deployment] → [App Restart] → [Auth Validation] → [Old Secret Rejected & New Secret Accepted]
```

---

## 2. JWT Secret Rotation Procedure

1. **Generate New Strong Secret**:
   ```bash
   openssl rand -hex 32
   ```
2. **Update Environment Configuration**:
   Update `JWT_SECRET` in production `.env` file or secrets manager.
3. **Graceful Application Restart**:
   ```bash
   docker compose -f backend/docker-compose.yml restart api worker-1 worker-2
   ```
4. **Validation Test**:
   - Verify old JWT tokens return HTTP 401 Unauthorized.
   - User re-logs in at `/api/auth/login` → New JWT token issued and accepted.

---

## 3. Database Credential Rotation Procedure

1. Create new database user in PostgreSQL:
   ```sql
   CREATE USER roadsos_v2 WITH PASSWORD 'new_secure_password_456';
   GRANT ALL PRIVILEGES ON DATABASE roadsos_db TO roadsos_v2;
   ```
2. Update `DATABASE_URL` in `.env`.
3. Restart API & Workers.
4. Revoke old database user access once all connections migrate.
