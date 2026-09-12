# RoadSOS Production Capacity & Resource Growth Forecast

**Forecast Horizon**: 12-Month Projections (v1.0.0 → v2.0.0)  
**Target Load**: 100,000 Active Citizens / 500 Paramedic Units

---

## 1. Resource Utilization & Growth Projection Matrix

| System Component | Current Baseline Usage | 6-Month Projected Load | 12-Month Projected Load | Scaling Action Plan |
| :--- | :--- | :--- | :--- | :--- |
| **API Containers** | 250MB RAM / 5% CPU | 500MB RAM / 15% CPU | 1.2GB RAM / 35% CPU | Horizontal container scaling (2 → 4 API nodes) |
| **Worker Fleet** | 2 Workers / 35% utilization | 4 Workers / 40% utilization | 6 Workers / 50% utilization | Enforce queue-depth auto-scaling |
| **PostgreSQL DB** | 900MB storage / 12 connections | 4.5GB storage / 30 connections | 15GB storage / 60 connections | Partition `triage_events` by month |
| **MinIO Storage** | 2.5GB storage | 15GB storage | 50GB storage | Apply 90-day S3 object expiration policy |

---

## 2. Resource Optimization Recommendation
- `SCALE`: Maintain PostgreSQL connection pool size scaling policy.
- `MONITOR`: MinIO offsite backup growth.
