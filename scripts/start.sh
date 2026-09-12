#!/usr/bin/env bash
set -e

echo "=== Starting RoadSOS Services via Docker Compose ==="
cd backend && docker compose up -d
echo "RoadSOS backend services are up and healthy!"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
