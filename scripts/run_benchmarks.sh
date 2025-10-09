#!/bin/bash
# Run agent benchmarks and log to LangSmith

set -e

cd "$(dirname "$0")/.."

# Load .env file if it exists
if [ -f .env ]; then
    echo "Loading environment from .env..."
    set -a  # automatically export all variables
    source .env
    set +a
fi

echo "============================================================"
echo "EstimAI Agent Benchmarks"
echo "============================================================"
echo ""

# Check for LangSmith API key
if [ -z "$LANGSMITH_API_KEY" ]; then
    echo "⚠️  LANGSMITH_API_KEY not set"
    echo "   Set it to enable tracing: export LANGSMITH_API_KEY=your-key"
    echo "   Continuing without LangSmith tracing..."
    echo ""
else
    echo "✅ LangSmith tracing enabled"
    echo "   Project: ${LANGSMITH_PROJECT:-estimai-takeoff}"
    echo "   View at: https://smith.langchain.com"
    echo ""
fi

# Activate venv
source backend/.venv/bin/activate

# Set environment for testing
export ESTIMAI_USE_VISION=1
export ESTIMAI_DEBUG=0
export ESTIMAI_SEED=42
export PYTHONPATH=.

echo "Running benchmarks..."
echo ""

# Run benchmark tests
pytest backend/tests/test_agent_benchmarks.py \
    -v \
    -m benchmark \
    --tb=short \
    "$@"

echo ""
echo "============================================================"
echo "Benchmarks complete!"
echo "============================================================"

if [ -n "$LANGSMITH_API_KEY" ]; then
    echo ""
    echo "View detailed traces at: https://smith.langchain.com"
fi
