#!/bin/bash
# scripts/run_tests.sh
# Run all tests with coverage report

set -euo pipefail

echo "🧪 Running Nexxi test suite..."

source .venv/bin/activate 2>/dev/null || true

# Unit tests (no external dependencies required)
echo ""
echo "── Unit Tests ──────────────────────────────────"
pytest tests/unit/ \
  -v \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=html:htmlcov \
  -m "not slow" \
  "$@"

echo ""
echo "📊 Coverage report: htmlcov/index.html"
echo "✅ Tests complete!"
