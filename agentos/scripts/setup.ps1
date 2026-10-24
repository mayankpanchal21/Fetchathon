# AgentOS — Windows Setup Script (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "⚡ AgentOS — Setup Environment (Windows 10/11)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$ROOT_DIR = Split-Path -Parent $PSScriptRoot
Set-Location $ROOT_DIR

# 1. Detect Python
$PYTHON_BIN = "python"
try {
    & $PYTHON_BIN --version
} catch {
    Write-Error "Python 3 is required. Please install Python 3.11 from python.org"
}

# 2. Virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python virtual environment in .venv..." -ForegroundColor Yellow
    & $PYTHON_BIN -m venv .venv
}

$VENV_PYTHON = Join-Path $ROOT_DIR ".venv\Scripts\python.exe"
$VENV_PIP = Join-Path $ROOT_DIR ".venv\Scripts\pip.exe"

Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
& $VENV_PIP install --upgrade pip
& $VENV_PIP install -r services\desktop-agent\requirements.txt -r services\fetch-agent\requirements.txt

Write-Host "Installing Playwright chromium browser..." -ForegroundColor Yellow
& (Join-Path $ROOT_DIR ".venv\Scripts\playwright.exe") install chromium

# 3. Frontend dependencies
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location "$ROOT_DIR\apps\desktop-ui"
npm.cmd install
Set-Location $ROOT_DIR

# 4. Environment config
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created default .env file." -ForegroundColor Green
}

if (-not (Test-Path "workspace")) {
    New-Item -ItemType Directory -Path "workspace" | Out-Null
}

Write-Host "==================================================" -ForegroundColor Green
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host "Run .\scripts\dev.ps1 to launch AgentOS." -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
