#!/usr/bin/env bash
# Run only the FastAPI backend (useful for development/debugging)

set -e  # Exit on error

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo "EPDM Vacuum Fixture - API Server"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run: ./scripts/setup_venv.sh"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Add src to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Get the local IP address
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo "Starting API server..."
echo ""
echo "  API:      http://${LOCAL_IP}:8000"
echo "  Docs:     http://${LOCAL_IP}:8000/docs"
echo "  ReDoc:    http://${LOCAL_IP}:8000/redoc"
echo ""

# Run with reload for development
python -m uvicorn epdm_vacuum.api_main:app --host 0.0.0.0 --port 8000 --reload


