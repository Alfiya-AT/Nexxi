#!/bin/bash
# scripts/setup.sh
# One-command setup for local development

set -euo pipefail

echo "🚀 Setting up Nexxi development environment..."

# ── Check Python version ─────────────────────────────

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED="3.11"

if [[ "$(printf '%s\n' "$REQUIRED" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED" ]]; then
  echo "❌ Python $REQUIRED+ required. Found: $PYTHON_VERSION"
  exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# ── Create virtual environment ───────────────────────

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  echo "✅ Virtual environment created at .venv/"
else
  echo "ℹ️  Virtual environment already exists"
fi

source .venv/bin/activate

# ── Install dependencies ─────────────────────────────

pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

# ── Set up .env ──────────────────────────────────────

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "⚠️  .env created from .env.example — FILL IN YOUR VALUES before running!"
else
  echo "ℹ️  .env already exists"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your HF_TOKEN and API_KEY"
echo "  2. source .venv/bin/activate"
echo "  3. python -m app.main"
echo "     (or: docker compose --env-file .env -f docker/docker-compose.yml up)"
