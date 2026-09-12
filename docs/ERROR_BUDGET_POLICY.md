# RoadSOS Error Budget & Production SLO Governance Policy

**Policy Version**: v1.0.0  
**Effective Date**: September 11, 2026  
**Target Availability**: 99.9% Monthly Availability (Error Budget = 43.2 minutes downtime / month)

---

## 1. Production Service Level Objectives (SLOs)

| Service Area | SLO Metric | Target Threshold | Measurement Period |
| :--- | :--- | :---: | :---: |
| **API Availability** | `/health` & `/api/ready` success rate | **>= 99.9%** | 30-Day Rolling Window |
| **Sync Triage Latency** | `POST /api/triage` latency | **p95 < 250ms, p99 < 500ms** | 30-Day Rolling Window |
| **Async Job Completion** | Triage job completion time | **p95 < 5s, p99 < 15s** | 30-Day Rolling Window |
| **Worker Processing** | Worker heartbeat latency | **< 30s** | Continuous |
| **Database Pool** | DB connection pool exhaustion | **< 1% failed connections** | 30-Day Rolling Window |

---

## 2. Error Budget Consumption & Freeze Thresholds

- **Error Budget Remaining > 50%**: Normal feature velocity & deployment releases allowed.
- **Error Budget Remaining 20% - 50%**: Heightened deployment scrutiny & peer review required.
- **Error Budget Remaining < 20%**: **FEATURE FREEZE**. All development shifts strictly to reliability engineering and bug fixes.
