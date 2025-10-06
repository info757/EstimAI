#!/usr/bin/env bash
set -euo pipefail

# Config
PDF="${1:-samples/bid_test.pdf}"
BASE="http://localhost:8000"
SESSION="demo"

echo "== MVP Smoke =="
echo "PDF: $PDF"
[ -f "$PDF" ] || { echo "Missing $PDF"; exit 1; }

echo "1) Agent propose"
AGENT=$(curl -s -F "file=@${PDF}" "$BASE/v1/agent/takeoff")
echo "$AGENT" | jq '.summary, .warnings' >/dev/null

echo "2) Spot-check one pipe has depth/trench stats"
echo "$AGENT" | jq '
  .proposed_review.payload.networks
  | to_entries[]
  | select(.key=="sanitary" or .key=="storm" or .key=="water")
  | .value.pipes[0]
  | {id, mat, dia_in, length_ft, avg_depth_ft, extra}
'

echo "3) Commit proposal"
echo "$AGENT" | jq '{session_id:"'"$SESSION"'", sheet_ref:"AUTO", payload:.proposed_review.payload}' \
| curl -s -X POST "$BASE/v1/takeoff/review" -H "Content-Type: application/json" -d @- \
| jq '.status,.upserted'

echo "4) Counts include depth buckets + trench CY"
curl -s "$BASE/v1/counts?session_id=$SESSION" \
| jq '.items[]
      | select(.category|test("pipe"))
      | {name,unit,quantity,
         avg_depth_ft:.attributes.avg_depth_ft,
         trench_cy:.attributes.trench_volume_cy,
         d0_5:.attributes.d_0_5, d5_8:.attributes.d_5_8,
         d8_12:.attributes.d_8_12, d12p:.attributes.d_12_plus}'

echo "5) Export summary PDF"
curl -s -X POST "$BASE/v1/export/summary" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"'"$SESSION"'"}' \
  --output summary_demo.pdf

ls -lh summary_demo.pdf
echo "== PASS =="
