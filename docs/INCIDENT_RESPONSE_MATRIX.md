# RoadSOS Incident Response & Operational Matrix

**System Target**: Production Stack (API, PostgreSQL 15, ML Worker Fleet, MinIO S3)  
**Effective Date**: September 11, 2026  

---

## Executive Overview

This matrix maps every production incident category to its severity level, detection method, automated recovery mechanism, manual operator escalation path, and target RTO/RPO limits.

---

## Incident Response Matrix

| Incident Category | Severity | Detection Metric / Alert | Automated Recovery Mechanism | Manual Escalation Procedure | Target RTO | Target RPO |
| :--- | :---: | :--- | :--- | :--- | :---: | :---: |
| **API Container Crash** | `critical` | `RoadSOS_API_Outage` | Docker auto-restart policy (`restart: unless-stopped`) | Run `docker compose restart api` | < 10 sec | 0 sec |
| **Worker Container Crash** | `warning` | `RoadSOS_WorkerFleetDegraded` | Surviving worker reclaims job via `FOR UPDATE SKIP LOCKED` | Run `docker compose restart worker-1 worker-2` | < 30 sec | 0 sec |
| **Queue Backlog Buildup** | `warning` | `RoadSOS_QueueBuildup` | Autoscaling worker fleet (`docker compose scale worker-1=2 worker-2=2`) | Scale workers horizontally | < 60 sec | 0 sec |
| **PostgreSQL Connection Drop** | `critical` | `RoadSOS_PostgreSQL_ConnectionFailure` | SQLAlchemy `pool_pre_ping=True` restores pool connections | Verify DB container status | < 15 sec | 0 sec |
| **MinIO S3 Outage** | `warning` | `disaster_recovery_remote_storage_available == 0` | Storage fallback active; API and primary database unaffected | Verify MinIO container & storage volume | < 2 min | < 5 min |
| **Stale Pending Job** | `critical` | `RoadSOS_OldestPendingJobStale` | Heartbeat timeout triggers stale job reclamation | Reset job status via SQL or restart workers | < 60 sec | 0 sec |
| **Database Corruption / Disaster** | `critical` | DB health check failure | WAL archive replication to off-site MinIO storage | Execute `UPGRADE_ROLLBACK_RUNBOOK.md` restore | < 15 min | < 5 min |
