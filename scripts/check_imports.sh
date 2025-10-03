#!/usr/bin/env bash
set -euo pipefail
echo "Checking for disallowed import prefixes..."
bad=$(grep -RnE '^(from|import) (app|vpdf)\b' backend || true)
if [[ -n "$bad" ]]; then
  echo "❌ Found disallowed imports:"
  echo "$bad"
  echo "Run: python scripts/fix_imports.py --write"
  exit 1
fi
echo "✅ Imports look good."
