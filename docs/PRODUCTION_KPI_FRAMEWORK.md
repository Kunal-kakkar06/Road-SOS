# RoadSOS Production KPI & Analytics Framework

**Framework Version**: v1.0.0  
**Effective Date**: September 11, 2026  
**Target Scope**: System Performance, Operational Value, AI Usability & Dispatch Velocity

---

## 1. Core Operational KPI Matrix

| KPI Dimension | Metric Name | Production Baseline | Target SLA / SLO | Measurement Frequency |
| :--- | :--- | :---: | :---: | :---: |
| **Triage Volume** | Total Triage Submissions | ~1,200 req/day | Scalable to 10,000/day | Continuous |
| **Routing Ratio** | Sync vs Async Utilization | 85% Sync / 15% Async | Bounded Async (< 20%) | Daily |
| **Completion Speed** | Sync Triage Processing Time | **< 10ms** | p95 < 250ms | Real-time Prometheus |
| **Queue Latency** | Async Worker Job Processing | **~1.1 seconds** | p95 < 5.0 seconds | Real-time Prometheus |
| **Worker Utilization**| Worker Fleet Capacity | 35% utilization | Optimal 30% - 70% | Continuous |
| **Dispatch Velocity** | Triage → Paramedic Assignment | **< 45 seconds** | < 2 minutes | Daily Audit |

---

## 2. Evidence-Based Action Recommendations

- **KEEP**: XGBoost + NLP + SHAP 10-feature inference engine (100% stable, < 10ms response).
- **SCALE**: Worker fleet horizontal scaling policy (2 → 4 workers on high queue depth).
- **OPTIMIZE**: IndexedDB offline emergency sync retry backoff schedule.
- **MONITOR**: MinIO offsite backup storage growth rate (~5GB/month forecast).
