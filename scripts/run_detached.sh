#!/bin/bash
#
# Run EPDM Vacuum services in detached tmux sessions
#
# This is an alternative to systemd services for development.
# Services will survive SSH disconnection but NOT system reboot.
#
# Usage:
#   ./scripts/run_detached.sh          # Start both services
#   ./scripts/run_detached.sh api      # Start only API
#   ./scripts/run_detached.sh web      # Start only Web
#   ./scripts/run_detached.sh stop     # Stop all
#   ./scripts/run_detached.sh attach   # Attach to API session
#
# To reconnect to sessions after SSH reconnection:
#   tmux attach -t epdm-api
#   tmux attach -t epdm-web
#
# To detach from session (keeps it running): Ctrl+B, then D
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

check_tmux() {
    if ! command -v tmux &> /dev/null; then
        log_warn "tmux is not installed. Installing..."
        sudo apt-get update && sudo apt-get install -y tmux
    fi
}

start_api() {
    if tmux has-session -t epdm-api 2>/dev/null; then
        log_warn "API session already exists. Use 'tmux attach -t epdm-api' to view"
        return
    fi
    
    log_info "Starting API server in tmux session 'epdm-api'..."
    tmux new-session -d -s epdm-api -c "$PROJECT_DIR" \
        "source venv/bin/activate && python -m epdm_vacuum.api_main; read -p 'Press Enter to close...'"
    log_info "API started. View with: tmux attach -t epdm-api"
}

start_web() {
    if tmux has-session -t epdm-web 2>/dev/null; then
        log_warn "Web session already exists. Use 'tmux attach -t epdm-web' to view"
        return
    fi
    
    # Check if web is built
    if [ ! -d "$PROJECT_DIR/web/.next" ]; then
        log_info "Building web frontend first..."
        cd "$PROJECT_DIR/web"
        npm install
        npm run build
    fi
    
    log_info "Starting Web server in tmux session 'epdm-web'..."
    tmux new-session -d -s epdm-web -c "$PROJECT_DIR/web" \
        "npm run start; read -p 'Press Enter to close...'"
    log_info "Web started. View with: tmux attach -t epdm-web"
}

stop_all() {
    log_info "Stopping all EPDM sessions..."
    tmux kill-session -t epdm-api 2>/dev/null && log_info "Stopped API" || true
    tmux kill-session -t epdm-web 2>/dev/null && log_info "Stopped Web" || true
}

show_status() {
    echo "=== EPDM tmux Sessions ==="
    tmux list-sessions 2>/dev/null | grep epdm || echo "No EPDM sessions running"
}

case "${1:-start}" in
    start)
        check_tmux
        start_api
        sleep 2
        start_web
        echo ""
        show_status
        echo ""
        log_info "Both services started in background tmux sessions"
        log_info "Attach with: tmux attach -t epdm-api (or epdm-web)"
        log_info "Detach with: Ctrl+B then D"
        ;;
    api)
        check_tmux
        start_api
        ;;
    web)
        check_tmux
        start_web
        ;;
    stop)
        stop_all
        ;;
    attach|api-attach)
        tmux attach -t epdm-api
        ;;
    web-attach)
        tmux attach -t epdm-web
        ;;
    status)
        show_status
        ;;
    restart)
        stop_all
        sleep 1
        check_tmux
        start_api
        sleep 2
        start_web
        show_status
        ;;
    *)
        echo "Usage: $0 {start|api|web|stop|attach|web-attach|status|restart}"
        exit 1
        ;;
esac

