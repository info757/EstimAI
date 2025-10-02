#!/usr/bin/env bash
set -e

# Start from project root
cd "$(dirname "$0")"

echo "🔹 Starting EstimAI backend server..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
  echo "❌ No .venv found. Creating virtual environment..."
  python3 -m venv .venv
  echo "✅ Virtual environment created"
fi

# Activate virtual environment
source .venv/bin/activate
echo "✅ Virtual environment activated"

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r backend/requirements.txt

# Set PYTHONPATH and start server
cd backend
export PYTHONPATH="${PWD}:${PYTHONPATH}"
echo "🚀 Starting FastAPI server at http://localhost:8000/docs"
echo "📁 Working directory: $(pwd)"
echo "🐍 Python path: $PYTHONPATH"

# Start the server
exec uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
