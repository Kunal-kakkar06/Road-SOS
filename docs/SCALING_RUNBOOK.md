# RoadSOS Production Scaling Runbook

**Target Infrastructure**: RoadSOS Live Production Stack (API, PostgreSQL 15, ML Worker Fleet)  
**Effective Date**: September 11, 2026  

---

## Executive Overview

This operational runbook provides step-by-step procedures for horizontally scaling the RoadSOS API and ML Worker fleets during traffic spikes, queue buildup, or capacity alerts.

---

## Scaling Procedures

### 1. Scaling the ML Worker Fleet (Queue Buildup)

#### Trigger Conditions
- Prometheus Alert: `RoadSOS_QueueBuildup` (Pending jobs > 20 for 3 minutes)
- Prometheus Alert: `RoadSOS_WorkerFleetCapacityExhausted` (Pending jobs > 100 with <= 2 workers)

#### Execution Command
To scale from 2 to 4 workers:
```bash
docker compose up -d --scale worker-1=2 --scale worker-2=2
```

#### Verification Steps
1. Verify active worker count:
   ```bash
   curl -s http://localhost:8000/api/ai/worker-health | jq .
   ```
2. Verify heartbeat registrations in database:
   ```sql
   SELECT worker_id, status, last_heartbeat FROM worker_heartbeats WHERE last_heartbeat >= NOW() - INTERVAL '1 minute';
   ```
3. Confirm pending queue depth decreases:
   ```bash
   curl -s http://localhost:8000/metrics | grep triage_jobs_total
   ```

---

### 2. Scaling Down ML Worker Fleet

#### Trigger Conditions
- Pending queue depth = 0 for > 15 minutes
- Traffic spike subsided

#### Execution Command
To scale down back to baseline 2 workers:
```bash
docker compose up -d --scale worker-1=1 --scale worker-2=1
```

---

### 3. Scaling API Replicas

#### Trigger Conditions
- HTTP request rate > 250 rps
- CPU utilization on `backend-api-1` > 80% for 5 minutes

#### Execution Command
```bash
docker compose up -d --scale api=3
```
