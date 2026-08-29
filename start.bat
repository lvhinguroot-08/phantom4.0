@echo off
echo Starting PHANTOM Services...

docker info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    docker compose up -d
    echo.
    echo PHANTOM Services Started in Docker!
    echo Open Dashboard: http://localhost:3000
    goto :eof
)

echo Docker not active. Starting via PowerShell Direct Host Mode...
powershell -ExecutionPolicy Bypass -File .\start.ps1
