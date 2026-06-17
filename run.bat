@echo off
title Gonzo AI Agent
cd /d "%~dp0"

echo === Gonzo AI Agent - Single Click Run ===
echo.

:: ── Check prerequisites ──
echo [1/5] Checking prerequisites...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)
echo    OK

:: ── Environment file ──
echo [2/5] Checking .env file...
if not exist backend\.env (
    if exist backend\.env.example (
        copy backend\.env.example backend\.env >nul
        echo    Created backend\.env from .env.example
        echo    ^>^> IMPORTANT: Edit backend\.env and set your OPENROUTER_API_KEY
    ) else (
        echo    WARNING: No .env file found. Using defaults.
    )
) else (
    echo    OK
)

:: ── Python virtual environment ──
echo [3/5] Setting up Python environment...
if not exist backend\venv (
    echo    Creating virtual environment...
    python -m venv backend\venv
)
call backend\venv\Scripts\activate.bat
pip install -q -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo    Retrying without quiet flag...
    pip install -r backend\requirements.txt
)
echo    OK

:: ── Frontend dependencies ──
echo [4/5] Setting up frontend...
cd frontend
if not exist node_modules (
    echo    Installing npm dependencies...
    call npm install
)
echo    OK
cd ..

:: ── Launch ──
echo [5/5] Starting servers...
echo.
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:5173
echo.
echo    Opening browser...
start http://localhost:5173

:: Start backend (in new window)
start "Gonzo Backend" cmd /c "cd /d "%~dp0backend" && call "%~dp0backend\venv\Scripts\activate.bat" && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: Start frontend dev server
cd frontend
call npm run dev
