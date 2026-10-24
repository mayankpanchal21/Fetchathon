#!/usr/bin/env bash
# ==============================================================================
# AgentOS — Headless Runner (No UI)
# Starts only the local desktop worker and Fetch.ai uAgent for Agentverse integration.
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "🤖 Starting AgentOS in Headless Mode (Agentverse Integration)"
echo "   No local web UI will be launched."
echo "============================================================"

# Resolve Python environment
PYTHON_BIN="$SCRIPT_DIR/agentos/.venv/bin/python"
UVICORN_BIN="$SCRIPT_DIR/agentos/.venv/bin/uvicorn"

if [ ! -f "$PYTHON_BIN" ]; then
    echo "⚠️  Virtual environment not found at $SCRIPT_DIR/agentos/.venv"
    echo "Running setup..."
    bash "$SCRIPT_DIR/agentos/scripts/setup.sh"
fi

# Load environment
if [ -f "$SCRIPT_DIR/agentos/.env" ]; then
    echo "📄 Loading environment from $SCRIPT_DIR/agentos/.env"
    export $(grep -v '^#' "$SCRIPT_DIR/agentos/.env" | xargs)
fi

echo "🚀 [1/2] Starting Desktop Execution Worker (FastAPI on port 8000)..."
cd "$SCRIPT_DIR/agentos/services/desktop-agent"
PYTHONPATH=. "$UVICORN_BIN" app.main:app --host 127.0.0.1 --port 8000 &
DESKTOP_PID=$!

sleep 2

echo "🚀 [2/2] Starting Fetch.ai uAgent (port 8001)..."
cd "$SCRIPT_DIR/agentos/services/fetch-agent"
"$PYTHON_BIN" agent.py &
FETCH_PID=$!

echo "============================================================"
echo "✅ AgentOS Headless Services Running!"
echo "   • Desktop API: http://127.0.0.1:8000"
echo "   • Fetch.ai uAgent: http://127.0.0.1:8001"
echo "   • Agent Address: agent1q06yqptvth3vc3wcfdrnl6p256ucrfsstx2arrq6gmrc2y7spdnw5twcjeg"
echo "   • Agentverse Chat: https://agentverse.ai or https://asi1.ai/chat"
echo "============================================================"
echo "Press [Ctrl+C] to stop all background services."

cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill "$DESKTOP_PID" 2>/dev/null || true
    kill "$FETCH_PID" 2>/dev/null || true
    echo "All services stopped."
    exit 0
}

trap cleanup INT TERM

wait
