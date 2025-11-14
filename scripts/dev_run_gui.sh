#!/usr/bin/env bash
# Development launcher for PyQt5 GUI application

set -e  # Exit on error

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo "EPDM Vacuum Fixture - GUI Launcher"
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

echo "Starting GUI application..."
echo ""
echo "======================================"
echo ""

# Run the application
python -m epdm_vacuum.app_main

echo ""
echo "Application terminated."

