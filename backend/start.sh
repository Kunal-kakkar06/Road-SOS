#!/bin/bash
set -e

echo "=== RoadSOS API Startup ==="

# Run Alembic migrations before starting the server
echo "Running Alembic migrations..."
alembic upgrade head && echo "Migrations complete." || echo "Migrations failed or already up-to-date, continuing..."

# Start the FastAPI server
echo "Starting uvicorn server on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
