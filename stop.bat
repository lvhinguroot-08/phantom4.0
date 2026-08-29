@echo off
echo Stopping PHANTOM Services...

docker info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    docker compose stop
    echo PHANTOM Docker containers stopped.
)

powershell -ExecutionPolicy Bypass -File .\stop.ps1
echo PHANTOM Services Stopped.
