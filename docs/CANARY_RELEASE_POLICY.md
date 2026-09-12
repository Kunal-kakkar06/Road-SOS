# RoadSOS Production Canary Release Policy & Automated Rollback Thresholds

**Effective Date**: September 11, 2026  

---

## Canary Traffic Phasing Schedule

| Phase | Traffic Share | Duration | Health Evaluation Metrics |
| :---: | :---: | :---: | :--- |
| **Phase 1** | 5% | 15 minutes | HTTP 5xx error rate, p95 latency |
| **Phase 2** | 25% | 30 minutes | Worker job completion rate, SHAP consistency |
| **Phase 3** | 50% | 1 hour | Queue depth, DB connection pool health |
| **Phase 4** | 100% (Full Release) | Final | Full operational monitoring |

---

## Automatic Rollback Trigger Thresholds

If ANY of the following thresholds are breached during a canary evaluation phase, an **automated rollback** is immediately executed:

1. **HTTP 5xx Server Error Rate**: > 0.50% over a 2-minute window.
2. **Sync Triage Latency (p95)**: > 50.0 ms.
3. **Async Job Error Rate**: > 1.0% of queued jobs entering `failed` status.
4. **Worker Heartbeat Stale Rate**: > 1 stale worker node.
5. **Database Connection Errors**: > 2 connection failures.
