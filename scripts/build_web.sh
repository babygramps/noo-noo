#!/usr/bin/env bash
# Build the Next.js frontend for production

set -e  # Exit on error

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "======================================"
echo "Building Web Frontend for Production"
echo "======================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed!"
    echo "Please install Node.js 18+ (https://nodejs.org)"
    exit 1
fi

cd web

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Build for production
echo "Building Next.js application..."
npm run build

echo ""
echo "======================================"
echo "Build complete!"
echo "======================================"
echo ""
echo "To start the production server, run:"
echo "  ./scripts/run_web.sh"
echo ""


