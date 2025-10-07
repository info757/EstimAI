#!/usr/bin/env bash
set -euo pipefail

echo "🧪 Running EstimAI CI tests..."

# Activate virtual environment
source backend/.venv/bin/activate

# Set environment variables
export APR_USE_APRYSE=1

echo "1️⃣ Boot test (must pass)"
PYTHONPATH=. pytest -q backend/tests/test_boot.py

echo "2️⃣ E2E smoke test (should pass)"
PYTHONPATH=. pytest -q backend/tests/test_mvp_e2e.py -m e2e

echo "3️⃣ Lint check (should pass)"
ruff check backend/ --fix

echo "4️⃣ Type check (should pass)"
mypy backend/ --ignore-missing-imports

echo "✅ All CI tests passed!"
