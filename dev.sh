#!/usr/bin/env bash
set -e

# Always start from the project root (the folder where this script lives)
cd "$(dirname "$0")"

echo "🔹 Starting EstimAI dev environment..."

# 1) Activate virtual environment
if [ -d ".venv" ]; then
  source .venv/bin/activate
  echo "✅ Virtualenv activated"
else
  echo "❌ No .venv found. Run: python3.11 -m venv .venv"
  exit 1
fi

# 2) Optional: keep pip & deps fresh
# pip install -U pip
# pip install -r requirements.txt || true

# 3) Run backend API
cd backend
echo "🚀 Running FastAPI server at http://localhost:8000/docs"
# Set PYTHONPATH to include the backend directory so imports work correctly
export PYTHONPATH="${PWD}:${PYTHONPATH}"
exec uvicorn app.main:app --reload --port 8000

