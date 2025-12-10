#!/usr/bin/env bash
# Production launcher for the web interface
# Starts both the FastAPI backend and Next.js frontend

set -e  # Exit on error

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo "EPDM Vacuum Fixture - Web Interface"
echo "======================================"
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Python virtual environment not found!"
    echo "Please run: ./scripts/setup_venv.sh"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed!"
    echo "Please install Node.js 18+ (https://nodejs.org)"
    exit 1
fi

# Check if web dependencies are installed
if [ ! -d "web/node_modules" ]; then
    echo "Installing web dependencies..."
    cd web
    npm install
    cd ..
fi

# Activate virtual environment
echo "Activating Python virtual environment..."
source venv/bin/activate

# Add src to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    
    # Kill background processes
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    
    echo "Cleanup complete."
}

trap cleanup EXIT

# Get the local IP address for display
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo "======================================"
echo "Starting services..."
echo "======================================"
echo ""

# Start FastAPI backend
echo "Starting FastAPI backend on port 8000..."
python -m uvicorn epdm_vacuum.api_main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "ERROR: Backend failed to start!"
    exit 1
fi

echo "Backend started (PID: $BACKEND_PID)"

# Start Next.js frontend
echo "Starting Next.js frontend on port 3000..."
cd web

# Use production build if available, otherwise dev mode
if [ -d ".next" ] && [ -f ".next/BUILD_ID" ]; then
    echo "Using production build..."
    npm run start &
else
    echo "No production build found, using development mode..."
    npm run dev &
fi

FRONTEND_PID=$!
cd ..

# Wait for frontend to start
sleep 3

# Check if frontend is running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "ERROR: Frontend failed to start!"
    exit 1
fi

echo "Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "======================================"
echo "Web interface ready!"
echo "======================================"
echo ""
echo "  Local:   http://localhost:3000"
echo "  Network: http://${LOCAL_IP}:3000"
echo ""
echo "  API:     http://${LOCAL_IP}:8000"
echo "  API Docs: http://${LOCAL_IP}:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo "======================================"
echo ""

# Wait for both processes
wait


