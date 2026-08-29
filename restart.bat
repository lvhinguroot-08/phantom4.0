@echo off
echo Restarting PHANTOM Services...

docker info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    docker compose restart
    echo PHANTOM Docker containers restarted.
    echo Dashboard: http://localhost:3000
    goto :eof
)

powershell -ExecutionPolicy Bypass -File .\restart.ps1
