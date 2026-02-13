#!/usr/bin/env bash
# Quick start script for Recruitment AI (Bash)
# Run from project root: ./quickstart.sh  (or: bash quickstart.sh)

set -e
cd "$(dirname "$0")"
PROJECT_ROOT="$(pwd)"

echo "=== Recruitment AI – Quick Start (Bash) ==="
echo ""

# Python check
if command -v python3 &>/dev/null; then
  PYTHON=python3
elif command -v python &>/dev/null; then
  PYTHON=python
else
  echo "Python not found. Install Python 3.11+ and try again."
  exit 1
fi
echo "Using: $PYTHON"

# Virtual environment
VENV_DIR="$PROJECT_ROOT/venv"
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating virtual environment..."
  "$PYTHON" -m venv "$VENV_DIR"
fi
echo "Activating venv..."
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# Dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt
echo "Dependencies OK."

# .env
if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  if [[ -f "$PROJECT_ROOT/.env.example" ]]; then
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo ""
    echo "Created .env from .env.example. Please edit .env and set AZURE_OPENAI_API_KEY and other variables."
    echo "Then run this script again to start the app."
    exit 0
  fi
  echo ".env not found. Create .env with at least AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT."
fi

echo ""
echo "Starting application..."
echo "Open http://localhost:5000 when ready."
echo ""
exec "$PYTHON" app.py
