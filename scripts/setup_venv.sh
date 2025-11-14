#!/usr/bin/env bash
# Setup script for EPDM Vacuum Fixture project
# This script creates a virtual environment and installs all dependencies

set -e  # Exit on error

echo "======================================"
echo "EPDM Vacuum Fixture - Setup Script"
echo "======================================"
echo ""

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Project root: $PROJECT_ROOT"
echo ""

# Check Python version
echo "[1/4] Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $PYTHON_VERSION"

# Create virtual environment
echo ""
echo "[2/4] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Virtual environment already exists. Removing old one..."
    rm -rf venv
fi
python3 -m venv venv
echo "Virtual environment created: $PROJECT_ROOT/venv"

# Activate virtual environment
echo ""
echo "[3/4] Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "[4/4] Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "======================================"
echo "Setup complete!"
echo "======================================"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the GUI application:"
echo "  ./scripts/dev_run_gui.sh"
echo ""
echo "To run the API server:"
echo "  ./scripts/dev_run_api.sh"
echo ""

