# RoadSOS Production Release Management & Versioning Policy

**System Target**: Production Stack (FastAPI, PostgreSQL 15 + PostGIS, 2+ Workers, MinIO S3)  
**Effective Date**: September 11, 2026  

---

## Executive Overview

This document specifies semantic versioning standards, release candidate promotion rules, artifact provenance hashing, change control approvals, and production release gate requirements for RoadSOS.

---

## Semantic Versioning Rules (SemVer 2.0.0)

RoadSOS follows strict Semantic Versioning (`MAJOR.MINOR.PATCH`):
- **MAJOR (`v1.0.0` -> `v2.0.0`)**: Breaking API payload changes or architecture overhaul (requires full steering committee sign-off).
- **MINOR (`v1.0.0` -> `v1.1.0`)**: Backward-compatible new features (e.g., additional telemetry counters, new non-breaking API fields).
- **PATCH (`v1.0.0` -> `v1.0.1`)**: Backward-compatible bug fixes, security patches, or performance optimizations.

---

## Production Release Gate Requirements

Every production release candidate MUST pass the following automated gates before deployment:

| Gate # | Gate Description | Verification Method | Pass Threshold |
| :---: | :--- | :--- | :---: |
| **1** | Full Pytest Regression Suite | `pytest tests/ -v` | **100% Passed (290/290)** |
| **2** | Alembic Schema Migration Check | `alembic check` | **0 Schema Drift** |
| **3** | ML Artifact Checksum Invariant | SHA-256 computation | **`e014884e...76001f1` Match** |
| **4** | Supply-Chain Security Audit | Dependency vulnerability scan | **0 High/Critical Vulnerabilities** |
| **5** | Zero-Downtime Upgrade Rehearsal | `test_step33_release_management.py` | **0 Lost Jobs, 0 Duplicate Events** |
| **6** | Rollback Drill Rehearsal | `test_step33_release_management.py` | **100% Automatic Recovery** |
