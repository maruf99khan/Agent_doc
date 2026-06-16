#!/usr/bin/env bash
set -e

# Build frontend if needed
if [ "$1" = "build" ]; then
    echo "=== Building frontend ==="
    cd frontend
    npm install
    npm run build
    cd ..
    echo "=== Frontend built ==="
    exit 0
fi

# Start backend
echo "=== Starting Gonzo backend ==="
cd backend
pip install -r requirements.txt -q
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
