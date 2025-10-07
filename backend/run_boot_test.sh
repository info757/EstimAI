#!/usr/bin/env bash
set -euo pipefail

echo "🧪 Running EstimAI boot test..."

# Activate virtual environment
source backend/.venv/bin/activate

# Set environment variables
export APR_USE_APRYSE=1

# Run the boot test
echo "Testing application startup and health endpoints..."
PYTHONPATH=. pytest -q backend/tests/test_boot.py

echo "✅ Boot test passed! Application starts successfully."
