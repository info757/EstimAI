#!/usr/bin/env bash
set -euo pipefail

# Test elevation extraction with a real PDF

PDF="${1:-samples/bid_test.pdf}"
SESSION="test_elev_$(date +%s)"
BASE="http://localhost:8000"

echo "═══════════════════════════════════════════════════"
echo "  Testing Elevation Extraction"
echo "═══════════════════════════════════════════════════"
echo ""
echo "PDF: $PDF"
echo "Session: $SESSION"
echo ""

[ -f "$PDF" ] || { echo "❌ Missing $PDF"; exit 1; }

echo "Running takeoff with elevation extraction..."
RESPONSE=$(curl -s \
  -F "session_id=${SESSION}" \
  -F "file=@${PDF}" \
  "$BASE/v1/agent/takeoff")

# Check status
STATUS=$(echo "$RESPONSE" | jq -r '.status')
if [ "$STATUS" != "completed" ]; then
  echo "❌ Agent failed:"
  echo "$RESPONSE" | jq '.'
  exit 1
fi

echo "✅ Agent completed"
echo ""

# Check pipe counts
STORM=$(echo "$RESPONSE" | jq '.proposed_review.payload.networks.storm.pipes | length')
SANITARY=$(echo "$RESPONSE" | jq '.proposed_review.payload.networks.sanitary.pipes | length')
WATER=$(echo "$RESPONSE" | jq '.proposed_review.payload.networks.water.pipes | length')

echo "Pipes detected:"
echo "  Storm: $STORM"
echo "  Sanitary: $SANITARY"
echo "  Water: $WATER"
echo ""

# Check depth data
echo "Checking depth extraction..."
echo ""

# Sample first storm pipe
if [ "$STORM" -gt 0 ]; then
  PIPE_DATA=$(echo "$RESPONSE" | jq '.proposed_review.payload.networks.storm.pipes[0]')
  PIPE_ID=$(echo "$PIPE_DATA" | jq -r '.id')
  AVG_DEPTH=$(echo "$PIPE_DATA" | jq -r '.avg_depth_ft')
  INVERT_IN=$(echo "$PIPE_DATA" | jq -r '.extra.invert_in_ft // "N/A"')
  INVERT_OUT=$(echo "$PIPE_DATA" | jq -r '.extra.invert_out_ft // "N/A"')
  GROUND=$(echo "$PIPE_DATA" | jq -r '.extra.ground_elev_ft // "N/A"')
  
  echo "Sample Storm Pipe:"
  echo "  ID: $PIPE_ID"
  echo "  Avg Depth: ${AVG_DEPTH}ft"
  echo "  Invert IN: ${INVERT_IN}ft"
  echo "  Invert OUT: ${INVERT_OUT}ft"
  echo "  Ground: ${GROUND}ft"
  echo ""
  
  if [ "$AVG_DEPTH" != "null" ] && [ "$AVG_DEPTH" != "0" ]; then
    echo "✅ Real depth calculated!"
  else
    echo "⚠️  Depth is null or 0 - check elevation extraction"
    echo "   This means invert elevations weren't found in PDF text"
  fi
fi

# Check QA flags
QA_FLAGS=$(echo "$RESPONSE" | jq '.summary.qa_flags')
echo ""
echo "QA Flags:"
echo "$QA_FLAGS" | jq '.'

# Count depth unavailable flags
DEPTH_UNAVAILABLE=$(echo "$QA_FLAGS" | jq -r '.DEPTH_UNAVAILABLE // 0')
echo ""
if [ "$DEPTH_UNAVAILABLE" -gt 0 ]; then
  echo "⚠️  $DEPTH_UNAVAILABLE pipes flagged as DEPTH_UNAVAILABLE"
  echo "   (Missing invert elevation text in PDF)"
else
  echo "✅ All pipes have depth data!"
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Elevation extraction test complete"
echo "═══════════════════════════════════════════════════"

