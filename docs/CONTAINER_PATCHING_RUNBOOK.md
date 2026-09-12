# RoadSOS Container Base Image Patching Runbook

**Runbook Version**: v1.0.0  
**Target Audience**: DevOps Engineers, SREs, Security Operations  
**Target Scope**: Docker base images, Linux security patches, base runtime updates

---

## 1. Objective & Patching Trigger

This runbook defines the operational steps to patch OS-level security vulnerabilities in RoadSOS Docker container base images (`python:3.10-slim`, `postgres:15-alpine`, `minio/minio`).

---

## 2. Step-by-Step Container Patching SOP

### Step 1: Update Base Image Digest in Dockerfile
```bash
# Pull latest stable base image
docker pull python:3.10-slim

# Inspect image digest
docker inspect --format='{{index .RepoDigests 0}}' python:3.10-slim
```

Update `Dockerfile`:
```dockerfile
FROM python:3.10-slim@sha256:latest_verified_sha256_digest
```

### Step 2: Build & Test Locally
```bash
# Rebuild containers locally
docker compose -f backend/docker-compose.yml build --no-cache

# Run full backend regression test suite
docker compose -f backend/docker-compose.yml run --rm api venv/bin/pytest tests/ -v
```

### Step 3: Rolling Production Container Replacement
```bash
# Apply rolling restart without downtime
docker compose -f backend/docker-compose.yml up -d --no-deps --build api
docker compose -f backend/docker-compose.yml up -d --no-deps --build worker-1
docker compose -f backend/docker-compose.yml up -d --no-deps --build worker-2
```

### Step 4: Verification
```bash
# Verify API health
curl -f http://localhost:8000/health
```
