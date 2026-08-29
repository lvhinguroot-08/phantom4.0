# ==============================================================================
# PHANTOM // Stop Platform Services
# ==============================================================================

Write-Host "Stopping PHANTOM services..." -ForegroundColor Cyan

$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    docker info > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        docker compose stop
        Write-Host "PHANTOM docker containers stopped." -ForegroundColor Green
    }
}

# Stop host python uvicorn on port 8000 if running
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process node -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*vite*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "PHANTOM host services stopped." -ForegroundColor Green
