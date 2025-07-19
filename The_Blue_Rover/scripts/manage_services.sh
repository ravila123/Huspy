#!/bin/bash
"""
Blue Rover Service Management Script

Manages systemd user services for Blue Rover components including:
- Battery monitoring service
- Camera streaming service

Usage:
  ./scripts/manage_services.sh install     # Install services
  ./scripts/manage_services.sh uninstall  # Remove services
  ./scripts/manage_services.sh start      # Start all services
  ./scripts/manage_services.sh stop       # Stop all services
  ./scripts/manage_services.sh restart    # Restart all services
  ./scripts/manage_services.sh status     # Show service status
  ./scripts/manage_services.sh logs       # Show service logs
"""

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
SERVICES=("blue-rover-battery" "blue-rover-camera")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if systemd user services are supported
check_systemd_support() {
    if ! command -v systemctl >/dev/null 2>&1; then
        log_error "systemctl not found. This system doesn't support systemd."
        exit 1
    fi
    
    # Enable lingering for user services to start at boot
    if ! loginctl show-user "$USER" -p Linger | grep -q "Linger=yes"; then
        log_info "Enabling user service lingering for boot startup..."
        if ! sudo loginctl enable-linger "$USER" 2>/dev/null; then
            log_warning "Could not enable lingering. Services won't start at boot."
        fi
    fi
}

# Create systemd user directory if it doesn't exist
ensure_systemd_dir() {
    if [[ ! -d "$SYSTEMD_USER_DIR" ]]; then
        log_info "Creating systemd user directory: $SYSTEMD_USER_DIR"
        mkdir -p "$SYSTEMD_USER_DIR"
    fi
}

# Install services
install_services() {
    log_info "Installing Blue Rover systemd services..."
    
    check_systemd_support
    ensure_systemd_dir
    
    # Copy service files
    for service in "${SERVICES[@]}"; do
        local service_file="$PROJECT_ROOT/config/systemd/${service}.service"
        local target_file="$SYSTEMD_USER_DIR/${service}.service"
        
        if [[ ! -f "$service_file" ]]; then
            log_error "Service file not found: $service_file"
            continue
        fi
        
        log_info "Installing $service service..."
        cp "$service_file" "$target_file"
        
        # Replace template variables
        sed -i "s|%h|$HOME|g" "$target_file"
        sed -i "s|%i|$USER|g" "$target_file"
        
        log_success "Installed $service.service"
    done
    
    # Reload systemd daemon
    log_info "Reloading systemd user daemon..."
    systemctl --user daemon-reload
    
    # Enable services for auto-start
    for service in "${SERVICES[@]}"; do
        log_info "Enabling $service service..."
        if systemctl --user enable "${service}.service"; then
            log_success "Enabled $service service"
        else
            log_error "Failed to enable $service service"
        fi
    done
    
    log_success "Service installation complete!"
    log_info "Use './scripts/manage_services.sh start' to start services"
}

# Uninstall services
uninstall_services() {
    log_info "Uninstalling Blue Rover systemd services..."
    
    # Stop and disable services
    for service in "${SERVICES[@]}"; do
        log_info "Stopping and disabling $service service..."
        systemctl --user stop "${service}.service" 2>/dev/null || true
        systemctl --user disable "${service}.service" 2>/dev/null || true
        
        # Remove service file
        local target_file="$SYSTEMD_USER_DIR/${service}.service"
        if [[ -f "$target_file" ]]; then
            rm "$target_file"
            log_success "Removed $service.service"
        fi
    done
    
    # Reload systemd daemon
    systemctl --user daemon-reload
    
    log_success "Service uninstallation complete!"
}

# Start services
start_services() {
    log_info "Starting Blue Rover services..."
    
    for service in "${SERVICES[@]}"; do
        log_info "Starting $service service..."
        if systemctl --user start "${service}.service"; then
            log_success "Started $service service"
        else
            log_error "Failed to start $service service"
        fi
    done
}

# Stop services
stop_services() {
    log_info "Stopping Blue Rover services..."
    
    for service in "${SERVICES[@]}"; do
        log_info "Stopping $service service..."
        if systemctl --user stop "${service}.service"; then
            log_success "Stopped $service service"
        else
            log_warning "$service service was not running"
        fi
    done
}

# Restart services
restart_services() {
    log_info "Restarting Blue Rover services..."
    
    for service in "${SERVICES[@]}"; do
        log_info "Restarting $service service..."
        if systemctl --user restart "${service}.service"; then
            log_success "Restarted $service service"
        else
            log_error "Failed to restart $service service"
        fi
    done
}

# Show service status
show_status() {
    log_info "Blue Rover Service Status:"
    echo
    
    for service in "${SERVICES[@]}"; do
        echo -e "${BLUE}=== $service ===${NC}"
        systemctl --user status "${service}.service" --no-pager -l || true
        echo
    done
}

# Show service logs
show_logs() {
    local service_filter=""
    if [[ $# -gt 1 ]]; then
        service_filter="$2"
    fi
    
    if [[ -n "$service_filter" ]]; then
        if [[ " ${SERVICES[*]} " =~ " ${service_filter} " ]]; then
            log_info "Showing logs for $service_filter service:"
            journalctl --user -u "${service_filter}.service" -f --no-pager
        else
            log_error "Unknown service: $service_filter"
            log_info "Available services: ${SERVICES[*]}"
            exit 1
        fi
    else
        log_info "Showing logs for all Blue Rover services:"
        local service_args=()
        for service in "${SERVICES[@]}"; do
            service_args+=("-u" "${service}.service")
        done
        journalctl --user "${service_args[@]}" -f --no-pager
    fi
}

# Show help
show_help() {
    cat << EOF
Blue Rover Service Management Script

USAGE:
    $0 <command> [options]

COMMANDS:
    install     Install systemd user services
    uninstall   Remove systemd user services
    start       Start all services
    stop        Stop all services
    restart     Restart all services
    status      Show service status
    logs [service]  Show service logs (optionally for specific service)
    help        Show this help message

SERVICES:
    blue-rover-battery   Battery monitoring service
    blue-rover-camera    Camera streaming service

EXAMPLES:
    $0 install                    # Install all services
    $0 start                      # Start all services
    $0 logs blue-rover-battery    # Show battery service logs
    $0 status                     # Show status of all services

EOF
}

# Main command processing
main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 1
    fi
    
    case "$1" in
        install)
            install_services
            ;;
        uninstall)
            uninstall_services
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$@"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"