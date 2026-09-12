# RoadSOS Production Capacity Planning & Threshold Matrix

**System Target**: Production Stack (FastAPI, PostgreSQL 15 + PostGIS, ML Worker Fleet, MinIO S3)  
**Effective Date**: September 11, 2026  

---

## Executive Overview

This document specifies concrete operational capacity limits, resource scaling triggers, queue depth thresholds, and PostgreSQL connection pool sizing guidelines for RoadSOS v1.0.0.

---

## Capacity Scaling Threshold Matrix

| Component | Metric | Normal Range | Scale Warning Threshold | Critical Action Trigger | Remediation Action |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **API Replicas** | Request Rate (req/sec) | 0 – 100 rps | > 250 rps | > 500 rps | Add API container replicas (`docker compose scale api=N`) |
| **API Memory** | RSS Memory (MB) | < 300 MB | > 512 MB | > 1024 MB | Restart API instance & inspect memory profile |
| **ML Worker Fleet** | Pending Queue Depth | 0 – 10 jobs | > 20 jobs | > 50 jobs | Scale ML worker fleet from 2 to 4+ instances |
| **ML Worker Fleet** | Job Latency | < 1.5 sec | > 3.0 sec | > 5.0 sec | Increase worker CPU allocation or add worker replicas |
| **PostgreSQL Pool** | Active Connections | 5 – 15 conns | > 25 conns | > 40 conns | Adjust `DB_POOL_SIZE` or implement PgBouncer pooler |
| **PostgreSQL Disk** | WAL / Data Storage | < 50 GB | > 100 GB | > 150 GB | Trigger WAL archive cleanup & prune old backup files |
| **Backup RPO** | Backup Age (seconds) | 0 – 180 sec | > 300 sec | > 600 sec | Trigger manual backup & check storage permissions |

---

## Database Connection Pool Sizing Formulation

```
DB_MAX_CONNECTIONS = (API_REPLICAS * DB_POOL_SIZE) + (WORKER_NODES * DB_POOL_SIZE) + OVERFLOW_MARGIN

Where:
- API_REPLICAS = 2 to 4
- WORKER_NODES = 2 to 6
- DB_POOL_SIZE = 5
- DB_MAX_OVERFLOW = 10
```

Recommended production PostgreSQL `max_connections` parameter: **100 connections**.

---

## Worker Fleet Sizing Formulation

$$\text{Required Workers} = \left\lceil \frac{\text{Async Request Rate (jobs/sec)} \times \text{Avg Processing Time (sec)}}{\text{Target Worker Utilization (0.70)}} \right\rceil$$

Example for 15 async jobs/sec with 1.0s processing time:
$$\text{Required Workers} = \left\lceil \frac{15 \times 1.0}{0.70} \right\rceil = 22 \text{ worker instances}$$
