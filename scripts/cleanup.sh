#!/usr/bin/env bash
set -e

echo "=== Cleaning up RoadSOS build artifacts and cache ==="
rm -rf frontend/dist frontend/node_modules/.cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
echo "Cleanup completed cleanly!"
