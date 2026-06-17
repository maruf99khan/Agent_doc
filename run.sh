#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "=== Gonzo AI Agent ==="
echo ""

# ── Check prerequisites ──
echo "[1/5] Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "ERROR: Python not found"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "ERROR: Node.js not found"; exit 1; }
echo "   OK"

# ── Environment file ──
echo "[2/5] Checking .env file..."
if [ ! -f backend/.env ]; then
    if [ -f backend/.env.example ]; then
        cp backend/.env.example backend/.env
        echo "   Created backend/.env from .env.example"
        echo "   >>> IMPORTANT: Edit backend/.env and set your OPENROUTER_API_KEY"
    else
        echo "   WARNING: No .env file found."
    fi
else
    echo "   OK"
fi

# ── Python virtual environment ──
echo "[3/5] Setting up Python environment..."
if [ ! -d backend/venv ]; then
    echo "   Creating virtual environment..."
    python3 -m venv backend/venv
fi
echo "   Installing dependencies..."
backend/venv/bin/pip install -q -r backend/requirements.txt
echo "   OK"

# ── Frontend dependencies ──
echo "[4/5] Setting up frontend..."
cd frontend
if [ ! -d node_modules ]; then
    echo "   Installing npm dependencies..."
    npm install
fi
echo "   OK"
cd ..

# ── Launch ──
echo "[5/5] Starting servers..."
echo ""
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
echo ""

# Open browser
sleep 2
open http://localhost:5173 2>/dev/null || xdg-open http://localhost:5173 2>/dev/null || true

# Start backend in background
backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start frontend dev server (foreground)
cd frontend
npm run dev

# Cleanup
kill $BACKEND_PID 2>/dev/null
