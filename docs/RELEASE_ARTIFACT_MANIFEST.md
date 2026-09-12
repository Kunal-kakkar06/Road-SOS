# RoadSOS Release Artifact Provenance Manifest

**Release Version**: RoadSOS v1.0.0 (Production Baseline)  
**Build Stamp**: 2026.09.11-001  
**Effective Date**: September 11, 2026  

---

## Immutable Artifact Hashes & Provenance

| Artifact / Component | Provenance Identifier / SHA-256 Hash | Verification Status |
| :--- | :--- | :---: |
| **Git Working Tree Commit** | Clean Release Commit | **VERIFIED** |
| **Alembic Schema Head Revision** | `c3d4e5f6a7b8` | **VERIFIED** |
| **XGBoost Model Weights (`fusion_triage.pkl`)** | `e014884ed8c2a537b8970af3fa1540ad8f85ac5b52846814373d0283b76001f1` | **VERIFIED** |
| **Frontend Production Asset Bundle** | `dist/index.html` + `dist/sw.js` PWA cache manifest | **VERIFIED** |
| **Python Requirements (`requirements.txt`)** | Deterministic lockfile | **VERIFIED** |
| **Frontend Package (`package.json`)** | Deterministic npm dependencies | **VERIFIED** |
| **Security Credential Audit** | 0 secrets/passwords exposed in release artifacts | **VERIFIED** |
