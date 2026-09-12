#!/usr/bin/env bash
set -e

echo "=== RoadSOS Environment Setup ==="
echo "1. Checking Node & Frontend dependencies..."
cd frontend && npm install
cd ..

echo "2. Building frontend dist..."
cd frontend && npm run build
cd ..

echo "3. Setup completed successfully!"
