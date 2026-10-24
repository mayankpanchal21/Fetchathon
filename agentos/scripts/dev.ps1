# AgentOS — Windows Development Launcher (PowerShell)
$ROOT_DIR = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT_DIR

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "⚡ Starting AgentOS Development Stack (Windows)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$VENV_PYTHON = Join-Path $ROOT_DIR ".venv\Scripts\python.exe"

# 1. Start Desktop Service
Write-Host "Starting Desktop Service on 127.0.0.1:8000..." -ForegroundColor Yellow
$desktopJob = Start-Process -FilePath $VENV_PYTHON -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000" -WorkingDirectory (Join-Path $ROOT_DIR "services\desktop-agent") -PassThru

# 2. Start Fetch.ai Agent
Write-Host "Starting Fetch.ai uAgent on 127.0.0.1:8001..." -ForegroundColor Yellow
$fetchJob = Start-Process -FilePath $VENV_PYTHON -ArgumentList "agent.py" -WorkingDirectory (Join-Path $ROOT_DIR "services\fetch-agent") -PassThru

# 3. Start Frontend
Write-Host "Starting React Dashboard on http://127.0.0.1:5173..." -ForegroundColor Green
Set-Location (Join-Path $ROOT_DIR "apps\desktop-ui")
try {
    npm.cmd run dev -- --host 127.0.0.1 --port 5173
} finally {
    Write-Host "Stopping background AgentOS processes..." -ForegroundColor Yellow
    Stop-Process -Id $desktopJob.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $fetchJob.Id -ErrorAction SilentlyContinue
}
