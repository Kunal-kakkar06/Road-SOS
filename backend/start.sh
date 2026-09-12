#!/bin/bash
set -e

echo "=== RoadSOS API Startup ==="
echo "DATABASE_URL scheme: ${DATABASE_URL%%:*}"

# Run Alembic migrations before starting the server
echo "Running Alembic migrations..."
if alembic upgrade head; then
    echo "✅ Migrations complete."
else
    echo "⚠️  Alembic migration failed - will rely on SQLAlchemy create_all fallback in app startup."
fi

# Start the FastAPI server
echo "Starting uvicorn server on port ${PORT:-8000}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
