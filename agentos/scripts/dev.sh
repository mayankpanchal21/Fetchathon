#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=================================================="
echo "⚡ Starting AgentOS Development Stack"
echo "=================================================="

# Function to clean up background processes on exit
cleanup() {
    echo ""
    echo "Stopping AgentOS services..."
    kill $(jobs -p) 2>/dev/null || true
    echo "AgentOS shutdown complete."
}
trap cleanup EXIT INT TERM

# 1. Start Local Desktop Agent Service
echo "Starting Local Desktop Service on http://127.0.0.1:8000..."
cd "$ROOT_DIR/services/desktop-agent"
PYTHONPATH=. "$ROOT_DIR/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 &
DESKTOP_PID=$!

# Wait for backend to be ready
echo "Waiting for desktop service health check..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "✅ Desktop Service is healthy."
        break
    fi
    sleep 0.5
done

# 2. Start Fetch.ai uAgent
echo "Starting Fetch.ai uAgent on http://127.0.0.1:8001..."
cd "$ROOT_DIR/services/fetch-agent"
"$ROOT_DIR/.venv/bin/python" agent.py &
FETCH_PID=$!

# 3. Start Frontend Dashboard
echo "Starting React Desktop Dashboard on http://127.0.0.1:5173..."
cd "$ROOT_DIR/apps/desktop-ui"
npm run dev -- --host 127.0.0.1 --port 5173

wait
