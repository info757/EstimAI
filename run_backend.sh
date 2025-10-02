#!/bin/bash
# Run EstimAI Backend
# This script ensures proper directory and environment setup

echo "🚀 Starting EstimAI Backend..."

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    echo "❌ Error: backend directory not found"
    echo "Please run this script from the repo root"
    exit 1
fi

# Change to backend directory
cd backend

# Activate virtual environment
echo "📦 Activating virtual environment..."
source ../.venv/bin/activate 2>/dev/null || true

# Check if uvicorn is available
if ! command -v uvicorn &> /dev/null; then
    echo "❌ Error: uvicorn not found"
    echo "Please install dependencies: pip install -r requirements.txt"
    exit 1
fi

# Run the backend
echo "🌐 Starting FastAPI server..."
echo "Backend will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo "Health check at: http://localhost:8000/healthz"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --reload --app-dir .