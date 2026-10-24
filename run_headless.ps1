# ==============================================================================
# AgentOS — Headless Runner for Windows (No UI)
# Starts only the local desktop worker and Fetch.ai uAgent for Agentverse integration.
# ==============================================================================

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🤖 Starting AgentOS in Headless Mode (Agentverse Integration)" -ForegroundColor Green
Write-Host "   No local web UI will be launched." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonBin = Join-Path $ScriptDir "agentos\.venv\Scripts\python.exe"
$UvicornBin = Join-Path $ScriptDir "agentos\.venv\Scripts\uvicorn.exe"

if (-Not (Test-Path $PythonBin)) {
    Write-Host "⚠️ Python virtual environment not found. Running setup..." -ForegroundColor Yellow
    & (Join-Path $ScriptDir "agentos\scripts\setup.ps1")
}

Write-Host "🚀 [1/2] Starting Desktop Execution Worker (FastAPI on port 8000)..." -ForegroundColor Green
$DesktopProc = Start-Process -FilePath $UvicornBin -ArgumentList "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory (Join-Path $ScriptDir "agentos\services\desktop-agent") -PassThru

Start-Sleep -Seconds 2

Write-Host "🚀 [2/2] Starting Fetch.ai uAgent (port 8001)..." -ForegroundColor Green
$FetchProc = Start-Process -FilePath $PythonBin -ArgumentList "agent.py" -WorkingDirectory (Join-Path $ScriptDir "agentos\services\fetch-agent") -PassThru

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ AgentOS Headless Services Running!" -ForegroundColor Green
Write-Host "   • Desktop API: http://127.0.0.1:8000"
Write-Host "   • Fetch.ai uAgent: http://127.0.0.1:8001"
Write-Host "   • Agent Address: agent1q06yqptvth3vc3wcfdrnl6p256ucrfsstx2arrq6gmrc2y7spdnw5twcjeg"
Write-Host "   • Agentverse Chat: https://agentverse.ai or https://asi1.ai/chat"
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Press [Ctrl+C] to stop all background services."

try {
    Wait-Process -Id $DesktopProc.Id, $FetchProc.Id
} finally {
    Stop-Process -Id $DesktopProc.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $FetchProc.Id -ErrorAction SilentlyContinue
}
