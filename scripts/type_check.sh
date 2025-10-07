#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Running type checking and linting..."

# Force working dir to repo root so 'backend.*' always resolves
cd "$(git rev-parse --show-toplevel)"

# Activate virtual environment if it exists
if [ -f "backend/.venv/bin/activate" ]; then
    source backend/.venv/bin/activate
    echo "Activating virtual environment..."
fi

echo "1️⃣ Type checking agent protocol (mypy)"
mypy backend/app/agent/types.py backend/app/agent/protocols.py backend/app/agent/__init__.py --ignore-missing-imports

echo "2️⃣ Linting agent module (ruff)"
ruff check backend/app/agent --fix

echo "3️⃣ Type checking contract tests"
mypy backend/tests/test_agent_contracts.py --ignore-missing-imports

echo "✅ Type checking and linting completed successfully!"
