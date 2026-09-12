# RoadSOS Database Preventive Maintenance Runbook

**Runbook Version**: v1.0.0  
**Target Engine**: PostgreSQL 15 + PostGIS  
**Maintenance Interval**: Weekly / Monthly Scheduled Maintenance

---

## 1. Preventive Maintenance Items & Health Thresholds

| Maintenance Task | Command / SQL Query | Target Metric / Threshold | Action if Threshold Exceeded |
| :--- | :--- | :--- | :--- |
| **Dead Tuple Cleanup** | `VACUUM ANALYZE triage_jobs;` | Dead tuples < 5% of total table rows | Run `VACUUM (ANALYZE, VERBOSE)` |
| **Unused Index Audit** | `SELECT indexrelname, idx_scan FROM pg_stat_user_indexes WHERE idx_scan = 0;` | 0 unused redundant indexes | Evaluate index deletion in migration |
| **Connection Pool Audit** | `SELECT count(*) FROM pg_stat_activity;` | Connections < 80% of `max_connections` | Adjust SQLAlchemy `pool_size` |
| **Long-Running Tx Audit** | `SELECT pid, now() - query_start FROM pg_stat_activity WHERE state != 'idle';` | Max query duration < 10 seconds | Terminate stuck query `pg_cancel_backend(pid)` |

---

## 2. Invariant Protection for Worker Queue Claiming

Database maintenance operations MUST preserve `FOR UPDATE SKIP LOCKED` worker queue claiming logic:
- Never hold exclusive locks (`LOCK TABLE triage_jobs IN ACCESS EXCLUSIVE MODE`) during peak operations.
- Run `VACUUM ANALYZE` concurrently without blocking row-level worker updates.
