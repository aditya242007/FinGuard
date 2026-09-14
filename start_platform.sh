#!/usr/bin/env bash
set -e

# Load environment variables if .env exists
if [ -f .env ]; then
  source .env
fi

echo "Starting FinGuard Platform..."

# Start the Python FastAPI backend for the AI agent in the background
echo "Starting AI Agent API on port 8000..."
python3 -m uvicorn src.m9_agent.api:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a second to ensure backend starts
sleep 2

# Start the Vite dashboard
echo "Starting Dashboard..."
cd dashboard
npm run dev &
FRONTEND_PID=$!

# Trap SIGINT to kill both processes
trap "kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT SIGTERM

echo "Platform running. Press Ctrl+C to stop."
wait
