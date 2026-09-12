# RoadSOS Production Release Upgrade & Rollback Runbook

**Target Infrastructure**: RoadSOS Production Stack  
**Effective Date**: September 11, 2026  

---

## Executive Overview

This document specifies the exact pre-flight, execution, validation, and rollback protocols for releasing schema or application code upgrades to RoadSOS production instances without downtime or data loss.

---

## Standard Production Upgrade Sequence

```
[Phase 1: Pre-Flight Safety Checks]
  ├── Verify git working tree is clean
  ├── Compute ML model SHA-256 (must equal e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1)
  └── Create pre-deployment database backup snapshot:
      pg_dump -h localhost -U roadsos -d roadsos_db | gzip > /tmp/pre_upgrade_backup.sql.gz

[Phase 2: Database Migration]
  ├── Run Alembic upgrade:
      alembic upgrade head
  └── Verify schema migration status:
      alembic check

[Phase 3: Rolling Application Deployment]
  ├── Restart API service instances:
      docker compose restart api
  └── Restart ML worker fleet instances:
      docker compose restart worker-1 worker-2

[Phase 4: Post-Deployment Verification]
  ├── Query liveness endpoint: curl -f http://localhost:8000/health
  ├── Query readiness endpoint: curl -f http://localhost:8000/api/ready
  └── Execute physical smoke test: python test_step21_production_smoke.py
```

---

## Emergency Rollback Procedure

If the post-deployment verification fails or an unrecoverable runtime defect is detected:

```bash
# 1. Roll back Alembic schema migration (1 step backward)
alembic downgrade -1

# 2. Re-deploy previous release candidate container images
docker compose up -d --build

# 3. If database state corruption occurred, restore pre-upgrade backup:
gunzip -c /tmp/pre_upgrade_backup.sql.gz | psql -h localhost -U roadsos -d roadsos_db

# 4. Confirm API liveness & readiness after rollback:
curl http://localhost:8000/api/ready
```
