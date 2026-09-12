# RoadSOS Production Deployment Standard Operating Procedure (SOP)

**Target Infrastructure**: Production Multi-Node Deployment  
**Effective Date**: September 11, 2026  

---

## Pre-Deployment Execution Sequence

1. **Verify Release Artifact Provenance**:
   - Confirm Git commit hash and tag.
   - Verify `fusion_triage.pkl` SHA-256 equals `e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1`.
2. **Execute Database Snapshot**:
   ```bash
   pg_dump -h localhost -U roadsos -d roadsos_db | gzip > /tmp/pre_deploy_$(date +%s).sql.gz
   ```
3. **Execute Alembic Schema Migration**:
   ```bash
   alembic upgrade head
   alembic check
   ```

---

## Rolling Deployment Sequence (Zero-Downtime)

1. **Rolling Worker Fleet Upgrade**:
   - Restart worker instances one at a time:
     ```bash
     docker compose restart worker-1
     # Wait for worker-1 heartbeat in worker_heartbeats table
     docker compose restart worker-2
     ```
2. **Rolling API Fleet Upgrade**:
   - Restart API instances sequentially behind load balancer:
     ```bash
     docker compose restart api
     curl -f http://localhost:8000/api/ready
     ```
3. **Frontend Bundle Deployment**:
   - Deploy `frontend/dist` assets and trigger Service Worker cache invalidation (`sw.js`).
