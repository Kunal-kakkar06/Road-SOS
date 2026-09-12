# RoadSOS SRE & Operations Handoff Manual

**Target Audience**: Site Reliability Engineers (SRE), System Administrators, DevOps Engineers  
**Release Version**: RoadSOS v1.0.0  
**Target Environment**: Production Multi-Container Orchestration (Docker Compose / Kubernetes)

---

## 1. Production Deployment SOP

### Environment Provisioning
1. Ensure Docker Engine 24+ and Docker Compose v2+ are installed.
2. Verify production `.env` is loaded into the deployment environment with non-default secrets.

```bash
# Production Container Deployment
docker compose -f backend/docker-compose.yml up -d --build

# Verify container health
docker compose -f backend/docker-compose.yml ps
```

---

## 2. Zero-Downtime Upgrade SOP (v1.0.0 → v1.0.1)

To perform a zero-downtime rolling deployment:

```bash
# 1. Apply database migrations
docker exec -it backend-api-1 alembic upgrade head

# 2. Rolling update API container
docker compose -f backend/docker-compose.yml up -d --no-deps --build api

# 3. Rolling update workers sequentially (worker 1 then worker 2)
docker compose -f backend/docker-compose.yml up -d --no-deps --build worker-1
docker compose -f backend/docker-compose.yml up -d --no-deps --build worker-2
```

---

## 3. Rollback Procedure SOP

If a release-blocking anomaly is detected:

```bash
# 1. Revert container image tags to prior validated release (v1.0.0)
docker compose -f backend/docker-compose.yml down

# 2. Restore database state if schema changes occurred
docker exec -i backend-db-1 psql -U roadsos -d roadsos_db < /backups/roadsos_pre_upgrade.sql

# 3. Restart v1.0.0 containers
docker compose -f backend/docker-compose.yml up -d
```

---

## 4. Worker Fleet Scaling SOP

Horizontal worker scaling based on queue depth:

- **Baseline Workload (< 50 pending jobs)**: 2 Workers
- **Moderate Workload (50 - 200 pending jobs)**: 4 Workers
- **Emergency Surge (> 200 pending jobs)**: 6 Workers

```bash
# Scale worker service to 4 instances
docker compose -f backend/docker-compose.yml up -d --scale worker-1=4
```

---

## 5. Prometheus Monitoring & Alert Thresholds

RoadSOS exposes metrics at `http://api:8000/metrics`. Key Prometheus alerts:

| Alert Name | Trigger Condition | Severity | Action |
| :--- | :--- | :---: | :--- |
| `HighAPIErrorRate` | 5xx error rate > 2% for 5 mins | **CRITICAL** | Check API container logs (`docker logs backend-api-1`) |
| `WorkerFleetDegraded` | Active workers < 2 for 3 mins | **CRITICAL** | Restart worker containers (`docker restart backend-worker-1-1`) |
| `QueueBacklogHigh` | Pending jobs > 100 for 5 mins | **WARNING** | Scale worker fleet to 4+ instances |
| `DatabasePoolExhausted` | DB connection pool usage > 90% | **HIGH** | Increase `DB_POOL_SIZE` in `.env` |

---

## 6. Incident Response & Logging Procedures

```bash
# View aggregated API logs
docker logs -f backend-api-1 --tail 100

# View aggregated Worker logs
docker logs -f backend-worker-1-1 --tail 100

# Inspect PostgreSQL database status
docker exec -it backend-db-1 psql -U roadsos -d roadsos_db -c "SELECT status, COUNT(*) FROM triage_jobs GROUP BY status;"
```
