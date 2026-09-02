# ==============================================================================
# PHANTOM // Start Platform Services
# ==============================================================================

Write-Host "Starting PHANTOM services..." -ForegroundColor Cyan

$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCmd) {
    docker info > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        docker compose up -d
        Write-Host "PHANTOM containers started." -ForegroundColor Green
        exit 0
    }
}

Write-Host "Docker daemon not running. Launching in Direct Portable Host Mode..." -ForegroundColor Yellow

# Start backend if not running
$backendRunning = $false
try {
    $r = Invoke-RestMethod -Uri "http://localhost:8000/health/live" -Method Get -TimeoutSec 1 -ErrorAction SilentlyContinue
    if ($r -and $r.status -eq "live") { $backendRunning = $true }
} catch {}

if (-not $backendRunning) {
    Write-Host "  [+] Starting FastAPI backend on port 8000..." -ForegroundColor Green
    $pythonExe = "python"
    if (Test-Path "backend\.venv\Scripts\python.exe") {
        $pythonExe = (Resolve-Path "backend\.venv\Scripts\python.exe").Path
    }
    Start-Process -FilePath $pythonExe -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory "backend"
}

# Start frontend dev server if not running
$frontendRunning = $false
try {
    $fr = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -TimeoutSec 1 -ErrorAction SilentlyContinue
    if ($fr -and $fr.StatusCode -eq 200) { $frontendRunning = $true }
} catch {}

if (-not $frontendRunning) {
    $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
    if ($npmCmd) {
        Write-Host "  [+] Starting frontend command center on port 3000..." -ForegroundColor Green
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory "frontend"
    }
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  PHANTOM IS ONLINE & READY" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "  Frontend Dashboard:      http://localhost:3000" -ForegroundColor White
Write-Host "  Backend OpenAPI Swagger: http://localhost:8000/api/v1/docs" -ForegroundColor White
Write-Host "  Health Live Probe:       http://localhost:8000/health/live" -ForegroundColor White
Write-Host "  Stream Gateway Playback: http://localhost:8000/api/v1/streams/CAM-001/live.m3u8" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Green
