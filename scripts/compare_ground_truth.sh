#!/usr/bin/env bash
set -euo pipefail

echo "🎯 EstimAI Ground Truth Comparison"
echo "===================================="
echo ""

# Force working dir to repo root
cd "$(git rev-parse --show-toplevel)"

# Activate virtual environment if it exists
if [ -f "backend/.venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source backend/.venv/bin/activate
fi

# Set deterministic seed
export ESTIMAI_SEED=42
export APR_USE_APRYSE=1

echo "Environment:"
echo "  ESTIMAI_SEED=$ESTIMAI_SEED (deterministic mode)"
echo "  APR_USE_APRYSE=$APR_USE_APRYSE"
echo ""

# Check if golden PDF exists
if [ ! -f "samples/280-utility-construction-plans.pdf" ]; then
    echo "❌ Golden PDF not found: samples/280-utility-construction-plans.pdf"
    exit 1
fi

echo "✅ Golden PDF found: samples/280-utility-construction-plans.pdf"
echo ""

# Run ground truth tests
echo "Running ground truth comparison tests..."
echo ""

PYTHONPATH=. pytest backend/tests/test_ground_truth.py \
    -v -s \
    -m ground_truth \
    --tb=short

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All ground truth checks passed!"
    echo ""
    echo "This confirms:"
    echo "  - LLM detection is deterministic with seed=42"
    echo "  - Pipe counts match expected values"
    echo "  - Linear feet within ±3% tolerance"
    echo "  - Depth calculations within ±5% tolerance"
    echo "  - Trench volumes within ±5% tolerance"
else
    echo "❌ Some ground truth checks failed"
    echo ""
    echo "Possible causes:"
    echo "  - PDF geometry changed"
    echo "  - Detection algorithm updated"
    echo "  - Depth calculation method changed"
    echo "  - Reference metrics need updating"
fi

exit $EXIT_CODE

