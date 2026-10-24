#!/usr/bin/env bash
set -e

echo "=================================================="
echo "⚡ AgentOS — Setup Environment (macOS / Linux)"
echo "=================================================="

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# 1. Check Python
PYTHON_BIN=""
if command -v python3.11 &>/dev/null; then
    PYTHON_BIN="python3.11"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
else
    echo "❌ Error: Python 3.11 or compatible Python 3 is required."
    exit 1
fi

echo "Using Python: $($PYTHON_BIN --version)"

# 2. Check Node & npm
if ! command -v node &>/dev/null || ! command -v npm &>/dev/null; then
    echo "❌ Error: Node.js and npm are required for desktop dashboard."
    exit 1
fi
echo "Using Node.js: $(node -v) / npm: $(npm -v)"

# 3. Create Python Virtual Environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment at .venv..."
    $PYTHON_BIN -m venv .venv
fi

echo "Installing Python dependencies for Desktop Agent and Fetch.ai uAgent..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r services/desktop-agent/requirements.txt -r services/fetch-agent/requirements.txt

# 4. Install Playwright browser
echo "Installing Playwright chromium browser binaries..."
.venv/bin/playwright install chromium

# 5. Install Frontend Dependencies
echo "Installing React frontend dependencies..."
cd apps/desktop-ui
npm install
cd "$ROOT_DIR"

# 6. Setup .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating default .env from .env.example..."
    cp .env.example .env
fi

# Ensure workspace folder exists
mkdir -p workspace

echo "=================================================="
echo "✅ Setup Complete!"
echo "To start development: ./scripts/dev.sh"
echo "=================================================="
