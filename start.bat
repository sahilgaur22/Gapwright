@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo               Starting Gapwright Local Stack
echo ========================================================
echo.

:: Move to root directory of the script
cd /d "%~dp0"

echo [1/4] Checking PostgreSQL database...
where docker >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo Starting PostgreSQL container via Docker...
    docker compose up -d db
    if %ERRORLEVEL% neq 0 (
        echo [WARNING] Docker start had an issue, trying local PostgreSQL service...
    ) else (
        echo Waiting for database container to be ready...
        timeout /t 3 /nobreak >nul
    )
) else (
    echo [INFO] Docker not found in PATH; using native PostgreSQL service on port 5432.
)

echo.
echo [2/4] Applying database migrations...
cd /d "%~dp0backend"
call .venv\Scripts\alembic.exe upgrade head
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Database migrations failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/4] Seeding demo dataset and credentials...
call .venv\Scripts\python.exe scripts\seed_demo.py
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Seed script reported an issue, continuing...
)

echo.
echo [4/4] Launching Backend API and Frontend Dashboard...

:: Start Backend API in a separate named command window
start "Gapwright API" /D "%~dp0backend" cmd /k ".venv\Scripts\uvicorn.exe app.main:app --reload --port 8000"

:: Start Frontend in a separate named command window
start "Gapwright Web" /D "%~dp0frontend" cmd /k "npm run dev"

echo.
echo ========================================================
echo Gapwright is now running!
echo.
echo   • Web Dashboard:    http://localhost:3000
echo   • API Documentation: http://localhost:8000/docs
echo   • API Healthcheck:   http://localhost:8000/healthz
echo.
echo Demo Accounts:
echo   • Educator:    educator@gapwright.edu    / Password123!
echo   • Policymaker: policymaker@highered.gov.in / Password123!
echo   • Student:     student@gapwright.edu     / Password123!
echo.
echo To shut down all services, run: end.bat
echo ========================================================
