# RoadSOS Production Dependency Maintenance Policy

**Policy Version**: v1.0.0  
**Effective Date**: September 11, 2026  
**Compliance Level**: MANDATORY  
**Target Scope**: Python backend dependencies (`requirements.txt`), Node.js frontend packages (`package-lock.json`), Docker base images (`Dockerfile`)

---

## 1. Executive Summary

This policy governs the selection, pinning, scanning, patching, and auditing of third-party software dependencies across the RoadSOS platform. The goal is to ensure zero high/critical vulnerabilities, prevent breaking API drift, and maintain supply chain integrity.

---

## 2. Dependency Pinning & Locking Rules

1. **Exact Version Pinning**: All production dependencies in `requirements.txt` and `package.json` MUST specify exact version numbers or tight patch bounds.
2. **Lockfile Enforcement**: `package-lock.json` MUST be committed to version control and enforced in CI/CD builds via `npm ci`.
3. **Base Image Provenance**: Base Docker images in `Dockerfile` (e.g. `python:3.10-slim`) MUST specify runtime version tags and SHA-256 image digests.
4. **Development vs Production Separation**: Development dependencies (e.g. pytest, linters) MUST be isolated from production runtime bundles.

---

## 3. Vulnerability Scanning & Advisory Lifecycle

- **Automated Scans**: Weekly automated scans via `pip audit` and `npm audit`.
- **SLA for Vulnerability Patching**:
  - **CRITICAL Vulnerability (CVSS 9.0 - 10.0)**: Patch deployed within 24 hours.
  - **HIGH Vulnerability (CVSS 7.0 - 8.9)**: Patch deployed within 7 days.
  - **MEDIUM/LOW Vulnerability (CVSS < 7.0)**: Evaluated for next scheduled sprint release.

---

## 4. Retraining & Baseline Protection

Dependency upgrades MUST NEVER alter the compiled ML artifact (`fusion_triage.pkl`), 10-feature input order, SHAP explainability calculations, or database schema migration contracts (`alembic`).
