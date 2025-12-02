#!/usr/bin/env bash
#===============================================================================
# EPDM Vacuum Fixture - Raspberry Pi GUI Launcher
#===============================================================================
#
# This script runs the PyQt5 GUI application on Raspberry Pi with TLB4 Modbus
# load cell transmitter support.
#
# Prerequisites:
#   1. USB-RS485 adapter connected (usually /dev/ttyUSB0)
#   2. User must be in 'dialout' group for serial port access:
#      sudo usermod -a -G dialout $USER
#      (Log out and back in after adding to group)
#   3. Virtual environment set up: ./scripts/setup_venv.sh
#
# Usage:
#   ./scripts/run_gui_pi.sh              # Use default Pi config
#   ./scripts/run_gui_pi.sh --debug      # Enable debug logging
#   ./scripts/run_gui_pi.sh --port /dev/ttyUSB1  # Custom serial port
#
#===============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}EPDM Vacuum Fixture - Raspberry Pi${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""
echo -e "Project root: ${GREEN}$PROJECT_ROOT${NC}"
echo ""

#-------------------------------------------------------------------------------
# Parse command line arguments
#-------------------------------------------------------------------------------
DEBUG_MODE=""
CUSTOM_PORT=""
CONFIG_FILE="$PROJECT_ROOT/src/epdm_vacuum/config/hardware_config_pi.yaml"

while [[ $# -gt 0 ]]; do
    case $1 in
        --debug|-d)
            DEBUG_MODE="true"
            shift
            ;;
        --port|-p)
            CUSTOM_PORT="$2"
            shift 2
            ;;
        --config|-c)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --debug, -d          Enable debug logging"
            echo "  --port, -p PORT      Use custom serial port (default: /dev/ttyUSB0)"
            echo "  --config, -c FILE    Use custom config file"
            echo "  --help, -h           Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

#-------------------------------------------------------------------------------
# Check prerequisites
#-------------------------------------------------------------------------------
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check if running on Linux (Pi)
if [[ "$(uname)" != "Linux" ]]; then
    echo -e "${RED}WARNING: This script is intended for Raspberry Pi (Linux).${NC}"
    echo -e "${YELLOW}For Windows, use: python -m epdm_vacuum.app_main${NC}"
fi

# Check virtual environment
if [ ! -d "venv" ]; then
    echo -e "${RED}ERROR: Virtual environment not found!${NC}"
    echo -e "${YELLOW}Please run: ./scripts/setup_venv.sh${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "Activating virtual environment..."
source venv/bin/activate

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}ERROR: Config file not found: $CONFIG_FILE${NC}"
    echo -e "${YELLOW}Using default hardware_config.yaml instead${NC}"
    CONFIG_FILE="$PROJECT_ROOT/src/epdm_vacuum/config/hardware_config.yaml"
fi

#-------------------------------------------------------------------------------
# Check USB-RS485 adapter / serial port
#-------------------------------------------------------------------------------
DEFAULT_PORT="/dev/ttyUSB0"
if [ -n "$CUSTOM_PORT" ]; then
    SERIAL_PORT="$CUSTOM_PORT"
else
    SERIAL_PORT="$DEFAULT_PORT"
fi

echo ""
echo -e "${YELLOW}Checking serial port...${NC}"

if [ -e "$SERIAL_PORT" ]; then
    echo -e "${GREEN}✓ Serial port found: $SERIAL_PORT${NC}"
    
    # Check permissions
    if [ -r "$SERIAL_PORT" ] && [ -w "$SERIAL_PORT" ]; then
        echo -e "${GREEN}✓ Serial port accessible${NC}"
    else
        echo -e "${RED}✗ Cannot access serial port!${NC}"
        echo -e "${YELLOW}  Add user to dialout group:${NC}"
        echo -e "${YELLOW}    sudo usermod -a -G dialout \$USER${NC}"
        echo -e "${YELLOW}  Then log out and back in.${NC}"
        echo ""
        echo -e "${YELLOW}  Or run with sudo (not recommended):${NC}"
        echo -e "${YELLOW}    sudo $0${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}! Serial port not found: $SERIAL_PORT${NC}"
    echo -e "${YELLOW}  TLB4 may not be connected. GUI will start in mock mode.${NC}"
    
    # List available serial ports
    echo ""
    echo -e "Available serial ports:"
    ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "  (none found)"
fi

#-------------------------------------------------------------------------------
# Set up environment
#-------------------------------------------------------------------------------
echo ""
echo -e "${YELLOW}Setting up environment...${NC}"

# Add src to PYTHONPATH so modules can be imported
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Override Modbus port if custom port specified
if [ -n "$CUSTOM_PORT" ]; then
    export MODBUS_PORT="$CUSTOM_PORT"
    echo -e "Using custom serial port: ${GREEN}$CUSTOM_PORT${NC}"
fi

# Enable debug if requested
if [ -n "$DEBUG_MODE" ]; then
    export LOG_LEVEL="DEBUG"
    echo -e "Debug mode: ${GREEN}ENABLED${NC}"
fi

# Set Qt platform if needed (for headless debugging)
# export QT_QPA_PLATFORM=xcb

# Set display for X11 forwarding (if using SSH with X forwarding)
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
    echo -e "Display set to: ${GREEN}:0${NC}"
fi

#-------------------------------------------------------------------------------
# Display configuration summary
#-------------------------------------------------------------------------------
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo -e "  Config file: ${GREEN}$CONFIG_FILE${NC}"
echo -e "  Serial port: ${GREEN}$SERIAL_PORT${NC}"
echo -e "  Python:      ${GREEN}$(which python)${NC}"
echo -e "  PYTHONPATH:  ${GREEN}$PYTHONPATH${NC}"

#-------------------------------------------------------------------------------
# Start the application
#-------------------------------------------------------------------------------
echo ""
echo -e "${BLUE}======================================${NC}"
echo -e "${GREEN}Starting GUI application...${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Run the application with the Pi config file
# The app will automatically use MODBUS_PORT environment variable if set
python -m epdm_vacuum.app_main --config "$CONFIG_FILE"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Application terminated normally.${NC}"
else
    echo -e "${RED}Application exited with code: $EXIT_CODE${NC}"
fi

exit $EXIT_CODE



