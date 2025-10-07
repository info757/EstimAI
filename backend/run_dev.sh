#!/usr/bin/env bash
set -euo pipefail

# Set environment variables
export APR_USE_APRYSE=${APR_USE_APRYSE:-1}
# Only export ESTIMAI_SEED if it's actually set
if [ -n "${ESTIMAI_SEED:-}" ]; then
    export ESTIMAI_SEED
fi

# Force working dir to repo root so 'backend.*' always resolves
cd "$(git rev-parse --show-toplevel)"

# Activate virtual environment if it exists
if [ -f "backend/.venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source backend/.venv/bin/activate
fi

# Start the server
echo "Starting EstimAI backend server..."
echo "Environment: APR_USE_APRYSE=$APR_USE_APRYSE"
echo "Working directory: $(pwd)"
echo "Python: $(which python)"
echo ""

uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --log-level info
