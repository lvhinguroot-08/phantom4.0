@echo off
echo ======================================================================
echo   PHANTOM // Automated Setup and Launch Bootstrapper
echo ======================================================================
echo.

if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo [+] Created .env configuration from .env.example
    )
)

echo [*] Checking Docker...
docker info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [+] Docker is active. Building and starting PHANTOM stack...
    docker compose up --build -d
    goto :ready
)

echo [i] Docker is not active. Running in Direct Portable Host Mode...
powershell -ExecutionPolicy Bypass -File .\setup.ps1
goto :eof

:ready
echo.
echo ======================================================================
echo   PHANTOM IS NOW RUNNING!
echo ======================================================================
echo   Frontend Dashboard:      http://localhost:3000
echo   Backend OpenAPI Swagger: http://localhost:8000/api/v1/docs
echo   Health Probe:            http://localhost:8000/health/live
echo   Stream Gateway Playback: http://localhost:8000/api/v1/streams/CAM-001/live.m3u8
echo ======================================================================
echo.
pause
