$ErrorActionPreference = "Stop"
$backendDir = Join-Path $PSScriptRoot "backend"
$pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Creating virtualenv..." -ForegroundColor Yellow
    python -m venv (Join-Path $backendDir ".venv")
    & $pythonExe -m pip install -q -r (Join-Path $backendDir "requirements.txt")
}

try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:8322/api/health" -Method Get -TimeoutSec 1 -ErrorAction Stop
    if ($res.status -eq "ok") {
        Write-Host "AutoJob backend already running on port 8322." -ForegroundColor Green
        exit 0
    }
} catch {}

Write-Host "Starting AutoJob backend on http://127.0.0.1:8322 ..." -ForegroundColor Green
Set-Location $backendDir
& $pythonExe run.py
