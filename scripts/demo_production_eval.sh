#!/usr/bin/env bash
#
# Demo: Production evaluation on a real PDF (without ground truth)
#
# Shows how to assess extraction quality using internal consistency,
# faithfulness, and completeness checks.

set -e

cd "$(dirname "$0")/.."

echo "🔍 Production Evaluation Demo"
echo "=============================="
echo ""
echo "This demonstrates evaluating takeoff quality WITHOUT ground truth."
echo "Useful for real-world PDFs where we don't have 'answers'."
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/_healthz > /dev/null 2>&1; then
    echo "❌ Backend not running. Start it with: ./backend/run_dev.sh"
    exit 1
fi

# Use a real PDF (280 utility plans)
PDF_PATH="280-utility-construction-plans.pdf"

if [ ! -f "$PDF_PATH" ]; then
    echo "⚠️  PDF not found: $PDF_PATH"
    echo "Using synthetic PDF instead..."
    PDF_PATH="synthetic/out/site_plan_medium.pdf"
    
    if [ ! -f "$PDF_PATH" ]; then
        echo "❌ No test PDF available. Generate one with:"
        echo "   cd synthetic && python gen_site_plan.py medium"
        exit 1
    fi
fi

echo "📄 Using PDF: $PDF_PATH"
echo ""

# Step 1: Run takeoff
echo "1️⃣  Running takeoff..."
SESSION_ID="demo_prod_eval_$(date +%s)"

RESPONSE=$(curl -s -X POST http://localhost:8000/v1/agent/takeoff \
    -F "file=@$PDF_PATH" \
    -F "session_id=$SESSION_ID")

echo "$RESPONSE" > /tmp/takeoff_result.json

# Check if takeoff succeeded
if echo "$RESPONSE" | jq -e '.summary.pipes_total' > /dev/null 2>&1; then
    PIPES_TOTAL=$(echo "$RESPONSE" | jq -r '.summary.pipes_total')
    echo "   ✅ Takeoff complete: $PIPES_TOTAL pipes detected"
else
    echo "   ❌ Takeoff failed"
    echo "$RESPONSE" | jq '.'
    exit 1
fi

echo ""

# Step 2: Extract PDF text for faithfulness check
echo "2️⃣  Extracting PDF text..."

# Use PyMuPDF to extract text
python3 << 'EOF' > /tmp/pdf_text.txt
import sys
try:
    import fitz  # PyMuPDF
    doc = fitz.open(sys.argv[1])
    text = ""
    for page in doc:
        text += page.get_text()
    print(text)
except ImportError:
    print("PyMuPDF not available")
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
EOF

if [ $? -eq 0 ]; then
    echo "   ✅ Text extracted"
else
    echo "   ⚠️  Text extraction failed (continuing without it)"
    echo "" > /tmp/pdf_text.txt
fi

echo ""

# Step 3: Run production evaluation
echo "3️⃣  Running production evaluation..."

PDF_TEXT=$(cat /tmp/pdf_text.txt)

EVAL_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/evaluate/production \
    -H "Content-Type: application/json" \
    -d @- << EOF
{
    "result": $(cat /tmp/takeoff_result.json),
    "pdf_text": $(echo "$PDF_TEXT" | jq -Rs .),
    "confidence_threshold": 0.70
}
EOF
)

echo "$EVAL_RESPONSE" > /tmp/eval_result.json

# Display results
echo ""
echo "📊 Evaluation Results"
echo "===================="
echo ""

CONFIDENCE=$(echo "$EVAL_RESPONSE" | jq -r '.confidence')
NEEDS_REVIEW=$(echo "$EVAL_RESPONSE" | jq -r '.needs_hitl_review')
RECOMMENDATION=$(echo "$EVAL_RESPONSE" | jq -r '.recommendation')

echo "Overall Confidence: $(printf "%.1f%%" $(echo "$CONFIDENCE * 100" | bc))"
echo "Needs HITL Review: $NEEDS_REVIEW"
echo "Recommendation: $RECOMMENDATION"
echo ""

echo "Quality Scores:"
echo "$EVAL_RESPONSE" | jq -r '.quality_scores | to_entries[] | "  \(.key): \(.value * 100 | round / 100)"'
echo ""

# Show flags if any
FLAG_COUNT=$(echo "$EVAL_RESPONSE" | jq '.flags | length')
if [ "$FLAG_COUNT" -gt 0 ]; then
    echo "⚠️  Flags ($FLAG_COUNT):"
    echo "$EVAL_RESPONSE" | jq -r '.flags[] | "  - [\(.score)] \(.message)"'
    echo ""
fi

# Interpretation
echo "💡 Interpretation"
echo "================"
echo ""

if (( $(echo "$CONFIDENCE >= 0.85" | bc -l) )); then
    echo "✅ HIGH CONFIDENCE - Ready for use"
    echo "   The extraction looks reliable. Spot check recommended."
elif (( $(echo "$CONFIDENCE >= 0.70" | bc -l) )); then
    echo "⚠️  ACCEPTABLE CONFIDENCE - Review recommended"
    echo "   The extraction is usable but should be reviewed by a human."
elif (( $(echo "$CONFIDENCE >= 0.50" | bc -l) )); then
    echo "⚠️  LOW CONFIDENCE - Human review required"
    echo "   Significant issues detected. Manual review is necessary."
else
    echo "❌ VERY LOW CONFIDENCE - Manual takeoff recommended"
    echo "   The automated extraction is unreliable. Consider manual takeoff."
fi

echo ""
echo "📁 Full results saved to:"
echo "   /tmp/takeoff_result.json"
echo "   /tmp/eval_result.json"
echo ""

