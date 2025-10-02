#!/bin/bash
# Run EstimAI Frontend
# This script ensures proper directory and environment setup

echo "🚀 Starting EstimAI Frontend..."

# Check if we're in the right directory
if [ ! -d "frontend" ]; then
    echo "❌ Error: frontend directory not found"
    echo "Please run this script from the repo root"
    exit 1
fi

# Change to frontend directory
cd frontend

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm not found"
    echo "Please install Node.js and npm"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run the frontend
echo "🌐 Starting Vite development server..."
echo "Frontend will be available at: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev
