#!/bin/bash
#
# EPDM Vacuum Fixture - Service Installation Script
# 
# This script installs systemd services so the application runs
# independently of SSH connections and survives sleep/reboot.
#
# Usage:
#   ./scripts/install_services.sh          # Install and start services
#   ./scripts/install_services.sh --remove # Remove services
#
# After installation, the services will:
#   - Start automatically on boot
#   - Restart automatically if they crash
#   - Run independently of SSH sessions
#
# View logs:
#   sudo journalctl -u epdm-api -f
#   sudo journalctl -u epdm-web -f
#   # Or check /var/log/epdm-api.log and /var/log/epdm-web.log
#

set -e

# Configuration - adjust these if your setup differs
INSTALL_DIR="${INSTALL_DIR:-/home/pi/noo-noo}"
SERVICE_USER="${SERVICE_USER:-pi}"
VENV_PATH="${INSTALL_DIR}/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if install directory exists
    if [ ! -d "$INSTALL_DIR" ]; then
        log_error "Installation directory not found: $INSTALL_DIR"
        log_error "Please set INSTALL_DIR environment variable or update this script"
        exit 1
    fi
    
    # Check if venv exists
    if [ ! -d "$VENV_PATH" ]; then
        log_warn "Python virtual environment not found at $VENV_PATH"
        log_info "Creating virtual environment..."
        sudo -u $SERVICE_USER python3 -m venv "$VENV_PATH"
        sudo -u $SERVICE_USER "$VENV_PATH/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    fi
    
    # Check if web build exists
    if [ ! -d "$INSTALL_DIR/web/.next" ]; then
        log_warn "Next.js build not found. Building web frontend..."
        cd "$INSTALL_DIR/web"
        sudo -u $SERVICE_USER npm install
        sudo -u $SERVICE_USER npm run build
    fi
    
    # Check if user exists
    if ! id "$SERVICE_USER" &>/dev/null; then
        log_error "User $SERVICE_USER does not exist"
        exit 1
    fi
    
    log_info "Prerequisites OK"
}

update_service_paths() {
    # Log to stderr so it doesn't get captured in the output
    echo -e "${GREEN}[INFO]${NC} Updating service files with installation paths..." >&2
    
    # Create temp copies with correct paths
    local api_service="/tmp/epdm-api.service"
    local web_service="/tmp/epdm-web.service"
    
    # Update API service
    sed -e "s|/home/pi/noo-noo|$INSTALL_DIR|g" \
        -e "s|User=pi|User=$SERVICE_USER|g" \
        -e "s|Group=pi|Group=$SERVICE_USER|g" \
        "$INSTALL_DIR/systemd/epdm-api.service" > "$api_service"
    
    # Update Web service
    sed -e "s|/home/pi/noo-noo|$INSTALL_DIR|g" \
        -e "s|User=pi|User=$SERVICE_USER|g" \
        -e "s|Group=pi|Group=$SERVICE_USER|g" \
        "$INSTALL_DIR/systemd/epdm-web.service" > "$web_service"
    
    echo "$api_service" "$web_service"
}

install_services() {
    check_root
    check_prerequisites
    
    log_info "Installing EPDM Vacuum Fixture services..."
    
    # Update paths in service files
    local services=$(update_service_paths)
    local api_service=$(echo $services | cut -d' ' -f1)
    local web_service=$(echo $services | cut -d' ' -f2)
    
    # Copy service files
    cp "$api_service" /etc/systemd/system/epdm-api.service
    cp "$web_service" /etc/systemd/system/epdm-web.service
    
    # Ensure user is in required groups for hardware access
    log_info "Adding user $SERVICE_USER to hardware groups..."
    usermod -aG spi,gpio,dialout $SERVICE_USER 2>/dev/null || log_warn "Could not add user to hardware groups (may not exist on this system)"
    
    # Ensure data directory exists with proper permissions
    mkdir -p "$INSTALL_DIR/data"
    chown -R $SERVICE_USER:$SERVICE_USER "$INSTALL_DIR/data"
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services (start on boot)
    systemctl enable epdm-api.service
    systemctl enable epdm-web.service
    
    # Start services
    log_info "Starting services..."
    systemctl start epdm-api.service
    sleep 2  # Give API time to initialize
    systemctl start epdm-web.service
    
    log_info "Services installed and started!"
    echo ""
    log_info "Service Status:"
    systemctl status epdm-api.service --no-pager || true
    echo ""
    systemctl status epdm-web.service --no-pager || true
    
    echo ""
    log_info "Useful commands:"
    echo "  View API logs:     sudo journalctl -u epdm-api -f"
    echo "  View Web logs:     sudo journalctl -u epdm-web -f"
    echo "  Restart API:       sudo systemctl restart epdm-api"
    echo "  Restart Web:       sudo systemctl restart epdm-web"
    echo "  Stop all:          sudo systemctl stop epdm-api epdm-web"
    echo ""
    log_info "Web interface available at: http://$(hostname -I | awk '{print $1}'):3000"
}

remove_services() {
    check_root
    
    log_info "Removing EPDM Vacuum Fixture services..."
    
    # Stop services
    systemctl stop epdm-api.service 2>/dev/null || true
    systemctl stop epdm-web.service 2>/dev/null || true
    
    # Disable services
    systemctl disable epdm-api.service 2>/dev/null || true
    systemctl disable epdm-web.service 2>/dev/null || true
    
    # Remove service files
    rm -f /etc/systemd/system/epdm-api.service
    rm -f /etc/systemd/system/epdm-web.service
    
    # Reload systemd
    systemctl daemon-reload
    
    log_info "Services removed"
}

show_status() {
    echo "=== EPDM API Service ==="
    systemctl status epdm-api.service --no-pager 2>/dev/null || echo "Not installed"
    echo ""
    echo "=== EPDM Web Service ==="
    systemctl status epdm-web.service --no-pager 2>/dev/null || echo "Not installed"
}

show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  install (default)  Install and start services"
    echo "  remove            Remove services"
    echo "  status            Show service status"
    echo "  restart           Restart all services"
    echo "  logs              Follow all logs"
    echo ""
    echo "Environment variables:"
    echo "  INSTALL_DIR       Installation directory (default: /home/pi/noo-noo)"
    echo "  SERVICE_USER      User to run services as (default: pi)"
}

# Main
case "${1:-install}" in
    install)
        install_services
        ;;
    remove|--remove|-r)
        remove_services
        ;;
    status)
        show_status
        ;;
    restart)
        check_root
        systemctl restart epdm-api.service
        sleep 2
        systemctl restart epdm-web.service
        show_status
        ;;
    logs)
        journalctl -u epdm-api -u epdm-web -f
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        log_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac

