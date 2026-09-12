#!/usr/bin/env bash
set -e

echo "=== Running RoadSOS Verification & Tests ==="
echo "Executing test suite inside backend container..."
cd backend && docker compose exec -T api pytest tests/ -v
