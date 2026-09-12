# RoadSOS Emergency Rollback Standard Operating Procedure (SOP)

**Target Infrastructure**: Production Multi-Node Deployment  
**Effective Date**: September 11, 2026  

---

## Rollback Execution Sequence

When post-deployment validation detects an unrecoverable defect or automated canary rollback triggers:

1. **Immediate Traffic Re-Routing**:
   - Re-route 100% of load balancer traffic to the baseline release image (`v1.0.0`).
2. **Rolling Worker Reversion**:
   - Revert worker container fleet to baseline release version.
3. **Database Migration Downgrade (If applicable)**:
   - Execute backward-compatible Alembic migration downgrade:
     ```bash
     alembic downgrade -1
     ```
4. **Data Integrity Audit**:
   - Verify 0 lost jobs in `triage_jobs` table.
   - Verify 0 duplicate events in `triage_events` table.
   - Confirm `/api/ready` returns HTTP 200 OK.
