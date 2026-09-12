# RoadSOS Disaster Recovery Quick Reference Sheet

**Target Audience**: On-Call SREs, Incident Commanders, Operations Leads  
**Targets**: RPO < 1 min, RTO < 5 mins  
**Release Version**: RoadSOS v1.0.0

---

## ⚡ Emergency 1-Page Recovery Cheat Sheet

### 1. Complete Database Failure & Restore

```bash
# Step 1: Drop corrupted database & recreate
docker exec -i backend-db-1 psql -U roadsos -c "DROP DATABASE IF EXISTS roadsos_db;"
docker exec -i backend-db-1 psql -U roadsos -c "CREATE DATABASE roadsos_db;"

# Step 2: Restore latest PostgreSQL backup
docker exec -i backend-db-1 psql -U roadsos -d roadsos_db < /backups/roadsos_latest.sql

# Step 3: Run Alembic verification
docker exec -it backend-api-1 alembic upgrade head
```

---

### 2. S3 / MinIO Object Storage Restoration

```bash
# Restore media assets and backup snapshots from MinIO offsite replica
mc mirror minio_replica/roadsos-backups /backups/
```

---

### 3. Worker Fleet Crash Recovery

```bash
# Restart hung worker fleet
docker compose -f backend/docker-compose.yml restart worker-1 worker-2

# Reclaim stale in-progress jobs (unclaimed > 5 mins)
docker exec -it backend-api-1 python3 -c "from services.triage_job_manager import reclaim_stale_jobs; reclaim_stale_jobs()"
```

---

### 4. Health & System Status Verification

```bash
# Test API Health Endpoint
curl -f http://localhost:8000/health

# Test Database Connection
docker exec -it backend-db-1 pg_isready -U roadsos -d roadsos_db
```
