@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo               Stopping Gapwright Local Stack
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/3] Stopping Frontend server on port 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo Terminating frontend process (PID %%a)...
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo [2/3] Stopping Backend API server on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Terminating backend process (PID %%a)...
    taskkill /f /pid %%a >nul 2>&1
)

:: Terminate named cmd windows if any remain open
taskkill /fi "WINDOWTITLE eq Gapwright API*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Gapwright Web*" /f >nul 2>&1

echo [3/3] Checking Docker database container...
where docker >nul 2>&1
if %ERRORLEVEL% equ 0 (
    docker compose stop db >nul 2>&1
    echo Database container stopped successfully.
) else (
    echo [INFO] Docker not used; native PostgreSQL service remains available.
)

echo.
echo ========================================================
echo Gapwright local stack has been completely stopped.
echo ========================================================
