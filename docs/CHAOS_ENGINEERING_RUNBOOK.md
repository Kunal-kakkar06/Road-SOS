# RoadSOS Production Chaos Engineering Runbook

**Target Environment**: RoadSOS Live Production Stack  
**Effective Date**: September 11, 2026  

---

## Executive Overview

This runbook documents the official Chaos Engineering execution framework for RoadSOS. It outlines fault injection protocols, safety stop-switches, observation procedures, and post-fault recovery criteria.

---

## Controlled Fault Injection Procedures

### 1. API Process Crash & Restart Simulation
- **Target Component**: FastAPI Application Server (`backend-api-1`)
- **Injection Protocol**: Send `SIGTERM` / restart Uvicorn process during active traffic.
- **Safety Boundary**: Background workers continue processing existing PostgreSQL queue independently.
- **Expected Recovery**: API liveness returns within < 3 seconds; pending jobs resume without loss.

### 2. ML Worker Crash Under Queue Backlog
- **Target Component**: Worker fleet (`backend-worker-1-1`, `backend-worker-2-1`)
- **Injection Protocol**: Kill 1 worker process while queue depth > 20 jobs.
- **Safety Boundary**: PostgreSQL `FOR UPDATE SKIP LOCKED` prevents job duplication.
- **Expected Recovery**: Surviving worker reclaims stale job after heartbeat threshold (< 2 min); zero duplicate events.

### 3. Database Connection Interruption
- **Target Component**: PostgreSQL 15 Container (`backend-db-1`)
- **Injection Protocol**: Temporarily drop network interface or restart DB container.
- **Safety Boundary**: SQLAlchemy `pool_pre_ping=True` handles connection drops transparently.
- **Expected Recovery**: Connection pool auto-recovers upon DB restoration; 0 transaction corruptions.

### 4. MinIO S3 Object Storage Failure
- **Target Component**: MinIO Off-Site Storage Target (`test-minio`)
- **Injection Protocol**: Stop MinIO container during backup replication cycle.
- **Safety Boundary**: MinIO failure is isolated; primary database and API remain 100% operational.
- **Expected Recovery**: Replication retries logged; primary application operational status unaffected.
