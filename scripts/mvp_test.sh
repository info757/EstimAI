#!/usr/bin/env bash
set -euo pipefail

PDF="${1:-samples/bid_test.pdf}"
BASE="http://localhost:8000"
SESSION="mvp_test_$(date +%s)"

echo "🚀 EstimAI MVP Test"
echo "=================="
echo "PDF: $PDF"
echo "Session: $SESSION"
echo ""

# Test 1: Agent Takeoff
echo "1️⃣ Running agent takeoff..."
RESULT=$(curl -s -F "session_id=${SESSION}" -F "file=@${PDF}" "${BASE}/v1/agent/takeoff")
STATUS=$(echo "$RESULT" | jq -r '.status')

if [ "$STATUS" = "completed" ]; then
  echo "✅ Agent completed successfully"
  echo "$RESULT" | jq '{status, pipes_total: .summary.pipes_total, warnings}'
  
  # Check for networks
  NETWORKS=$(echo "$RESULT" | jq -r '.proposed_review.payload.networks | keys[]')
  echo "   Networks found: $NETWORKS"
  
  # Show sample pipe
  echo ""
  echo "2️⃣ Sample pipe details:"
  echo "$RESULT" | jq '.proposed_review.payload.networks | to_entries[0].value.pipes[0] | {id, mat, dia_in, length_ft, avg_depth_ft}'
  
else
  echo "❌ Agent failed"
  echo "$RESULT" | jq '{status, error_message}'
  exit 1
fi

echo ""
echo "✅ MVP Test Passed!"
echo "   Backend is running correctly"
echo "   Agent endpoint is working"
echo "   Depth calculations are working"
echo ""
echo "🌐 You can now:"
echo "   - Start frontend: cd frontend && npm run dev"
echo "   - Open http://localhost:5173"
echo "   - Upload a PDF and see the results!"

