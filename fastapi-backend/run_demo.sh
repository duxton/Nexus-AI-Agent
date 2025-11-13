#!/bin/bash

echo "🎯 Conversational Memory System Demo"
echo "====================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "✅ Python 3 found"

# Install dependencies if needed
echo "📦 Installing dependencies..."
pip install fastapi uvicorn pydantic python-multipart pytest pytest-asyncio httpx

echo ""
echo "🧪 Running basic memory system tests..."
python test_memory_basic.py

echo ""
echo "🚀 Starting FastAPI server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs will be available at: http://localhost:8000/docs"
echo ""
echo "To test the API manually:"
echo "curl -X POST 'http://localhost:8000/chat' -H 'Content-Type: application/json' -d '{\"message\": \"Is there an outlet in Petaling Jaya?\"}'"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload