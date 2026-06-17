#!/usr/bin/env python3
"""Single-click runner for Gonzo AI Agent (cross-platform)."""

import os
import sys
import subprocess
import time
import webbrowser
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / "venv"
VENV_PYTHON = VENV / ("Scripts" if os.name == "nt" else "bin") / "python"
VENV_PIP = VENV / ("Scripts" if os.name == "nt" else "bin") / "pip"

def step(n, total, label):
    print(f"\n[{n}/{total}] {label}...")

def run(cmd, cwd=None, capture=False):
    kwargs = dict(cwd=str(cwd or ROOT), shell=True)
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    result = subprocess.run(cmd, **kwargs)
    return result

def check_prereqs():
    step(1, 5, "Checking prerequisites")
    if shutil.which("python") or shutil.which("python3"):
        print("   Python: OK")
    else:
        print("ERROR: Python not found. Install Python 3.10+ from https://python.org")
        sys.exit(1)
    if shutil.which("node"):
        print("   Node:  OK")
    else:
        print("ERROR: Node.js not found. Install Node.js 18+ from https://nodejs.org")
        sys.exit(1)

def setup_env():
    step(2, 5, "Checking .env file")
    env_file = BACKEND / ".env"
    env_example = BACKEND / ".env.example"
    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print(f"   Created {env_file}")
            print("   >>> IMPORTANT: Edit backend/.env and set your OPENROUTER_API_KEY")
        else:
            print("   WARNING: No .env file found. Using defaults.")
    else:
        print("   OK")

def setup_python():
    step(3, 5, "Setting up Python environment")
    if not VENV.exists():
        print("   Creating virtual environment...")
        run(f"python -m venv \"{VENV}\"")
    print("   Installing dependencies...")
    run(f"\"{VENV_PIP}\" install -q -r \"{BACKEND / 'requirements.txt'}\"")
    print("   OK")

def setup_frontend():
    step(4, 5, "Setting up frontend")
    if not (FRONTEND / "node_modules").exists():
        print("   Installing npm dependencies...")
        run("npm install", cwd=FRONTEND)
    print("   OK")

def launch():
    step(5, 5, "Starting servers")
    backend_url = "http://localhost:8000"
    frontend_url = "http://localhost:5173"
    print(f"\n   Backend:  {backend_url}")
    print(f"   Frontend: {frontend_url}\n")

    # Start backend
    backend_cmd = f"\"{VENV_PYTHON}\" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
    subprocess.Popen(backend_cmd, cwd=str(BACKEND), shell=True)

    # Wait a moment then open browser
    time.sleep(2)
    webbrowser.open(frontend_url)

    # Start frontend dev server (foreground)
    os.chdir(str(FRONTEND))
    try:
        subprocess.run("npm run dev", shell=True)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    os.chdir(str(ROOT))
    print("=== Gonzo AI Agent ===")
    check_prereqs()
    setup_env()
    setup_python()
    setup_frontend()
    launch()
