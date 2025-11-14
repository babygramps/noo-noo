#!/usr/bin/env bash
# Development launcher for Flask API server

set -e  # Exit on error

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo "EPDM Vacuum Fixture - API Launcher"
echo "======================================"
echo ""
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run: ./scripts/setup_venv.sh"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Add src to PYTHONPATH so modules can be imported
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Flask environment variables
export FLASK_APP=epdm_vacuum.api_main
export FLASK_ENV=development

echo "Starting Flask API server..."
echo "API will be available at: http://0.0.0.0:8000"
echo ""
echo "======================================"
echo ""

# Run the Flask application with hot reload enabled
flask run --host=0.0.0.0 --port=8000

echo ""
echo "API server terminated."

