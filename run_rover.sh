#!/bin/bash
#
# Blue Rover Unified Launcher Script
#
# This script provides a unified entry point for all Blue Rover control modes
# with proper virtual environment activation, error handling, process management,
# and cleanup on exit.
#
# Usage:
#     ./run_rover.sh [mode] [options]
#
# Modes:
#     manual   - Keyboard-based manual control
#     ps5      - PS5 DualSense controller control
#     monitor  - Battery monitoring only
#     web      - Web interface (camera stream + basic controls)
#
# Options:
#     --config FILE    - Use specific configuration file
#     --debug          - Enable debug logging
#     --help           - Show this help message
#
# Examples:
#     ./run_rover.sh manual
#     ./run_rover.sh ps5 --debug
#     ./run_rover.sh monitor --config config/rover_config_development.json
#     ./run_rover.sh web
#

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
LOG_DIR="${SCRIPT_DIR}/logs"
PID_FILE="${LOG_DIR}/rover.pid"
CONFIG_FILE=""
DEBUG_MODE=false
ROVER_MODE=""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_debug() {
    if [[ "$DEBUG_MODE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $1" >&2
    fi
}

# Show help message
show_help() {
    cat << 'EOF'
Blue Rover Unified Launcher

USAGE:
    ./run_rover.sh [MODE] [OPTIONS]

MODES:
    manual      Keyboard-based manual control
                Controls: w/s (speed), a/d (steer), i/k/j/l (camera), t (photo), q (quit)
    
    ps5         PS5 DualSense controller control
                Controls: L/R sticks, L2/R2 triggers, Square (stop), Options (quit)
    
    monitor     Battery monitoring only
                Continuously monitors and logs battery voltage with alerts
    
    web         Web interface mode
                Provides browser-based control and camera streaming

OPTIONS:
    --config FILE    Use specific configuration file
    --debug          Enable debug logging and verbose output
    --help           Show this help message

EXAMPLES:
    ./run_rover.sh manual
    ./run_rover.sh ps5 --debug
    ./run_rover.sh monitor --config config/rover_config_development.json
    ./run_rover.sh web

REQUIREMENTS:
    - Virtual environment must be set up (run ./setup.sh first)
    - Hardware must be connected and configured
    - For PS5 mode: Controller must be paired via Bluetooth

LOGS:
    Runtime logs are saved to: logs/
    Process PID file: logs/rover.pid

EOF
}

# Parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            manual|ps5|monitor|web)
                if [[ -n "$ROVER_MODE" ]]; then
                    log_error "Multiple modes specified. Please specify only one mode."
                    exit 1
                fi
                ROVER_MODE="$1"
                shift
                ;;
            --config)
                if [[ -n "${2:-}" ]]; then
                    CONFIG_FILE="$2"
                    shift 2
                else
                    log_error "--config requires a file path"
                    exit 1
                fi
                ;;
            --debug)
                DEBUG_MODE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                log_error "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Default to manual mode if no mode specified
    if [[ -z "$ROVER_MODE" ]]; then
        ROVER_MODE="manual"
        log_info "No mode specified, defaulting to manual control"
    fi
}

# Check system requirements
check_requirements() {
    log_debug "Checking system requirements..."

    # Check if we're on a Raspberry Pi
    if [[ ! -f /proc/device-tree/model ]] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        log_warn "Not running on Raspberry Pi - some hardware features may not work"
    fi

    # Check virtual environment
    if [[ ! -d "$VENV_DIR" ]]; then
        log_error "Virtual environment not found at $VENV_DIR"
        log_error "Please run ./setup.sh first to set up the environment"
        exit 1
    fi

    # Check Python in virtual environment
    if [[ ! -f "$VENV_DIR/bin/python" ]]; then
        log_error "Python not found in virtual environment"
        log_error "Please run ./setup.sh to reinstall the environment"
        exit 1
    fi

    # Create logs directory
    mkdir -p "$LOG_DIR"

    # Check configuration file if specified
    if [[ -n "$CONFIG_FILE" ]] && [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi

    log_debug "System requirements check passed"
}

# Activate virtual environment
activate_venv() {
    log_debug "Activating virtual environment..."
    
    # Source the virtual environment
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    
    # Verify activation
    if [[ "$VIRTUAL_ENV" != "$VENV_DIR" ]]; then
        log_error "Failed to activate virtual environment"
        exit 1
    fi
    
    log_debug "Virtual environment activated: $VIRTUAL_ENV"
}

# Check hardware connectivity
check_hardware() {
    log_debug "Checking hardware connectivity..."
    
    case "$ROVER_MODE" in
        ps5)
            # Check for PS5 controller
            if ! python -c "from pydualsense import pydualsense; ds = pydualsense(); ds.init(); print('PS5 controller check:', 'OK' if ds.connected() else 'FAIL'); ds.close()" 2>/dev/null; then
                log_warn "PS5 controller not detected"
                log_warn "Make sure the controller is paired and connected via Bluetooth"
                log_warn "You can continue, but the controller may not work"
            else
                log_debug "PS5 controller connectivity check passed"
            fi
            ;;
        manual|monitor|web)
            # Check basic PicarX connectivity
            if ! python -c "from picarx import Picarx; px = Picarx(); print('PicarX check: OK')" 2>/dev/null; then
                log_warn "PicarX hardware not detected"
                log_warn "Some features may not work without proper hardware"
            else
                log_debug "PicarX hardware connectivity check passed"
            fi
            ;;
    esac
}

# Set up signal handlers for graceful shutdown
setup_signal_handlers() {
    log_debug "Setting up signal handlers..."
    
    # Function to handle shutdown signals
    cleanup_and_exit() {
        local signal_name="$1"
        log_info "Received $signal_name signal, shutting down gracefully..."
        
        # Kill the rover process if it's running
        if [[ -f "$PID_FILE" ]]; then
            local rover_pid
            rover_pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
            if [[ -n "$rover_pid" ]] && kill -0 "$rover_pid" 2>/dev/null; then
                log_info "Stopping rover process (PID: $rover_pid)..."
                kill -TERM "$rover_pid" 2>/dev/null || true
                
                # Wait for graceful shutdown
                local count=0
                while kill -0 "$rover_pid" 2>/dev/null && [[ $count -lt 10 ]]; do
                    sleep 1
                    ((count++))
                done
                
                # Force kill if still running
                if kill -0 "$rover_pid" 2>/dev/null; then
                    log_warn "Force killing rover process..."
                    kill -KILL "$rover_pid" 2>/dev/null || true
                fi
            fi
            rm -f "$PID_FILE"
        fi
        
        log_info "Cleanup complete"
        exit 0
    }
    
    # Set up signal traps
    trap 'cleanup_and_exit "SIGINT"' INT
    trap 'cleanup_and_exit "SIGTERM"' TERM
    trap 'cleanup_and_exit "EXIT"' EXIT
}

# Build command line arguments for Python scripts
build_python_args() {
    local args=()
    
    if [[ "$DEBUG_MODE" == "true" ]]; then
        args+=(--debug)
    fi
    
    if [[ -n "$CONFIG_FILE" ]]; then
        args+=(--config "$CONFIG_FILE")
    fi
    
    # Handle empty array case
    if [[ ${#args[@]} -eq 0 ]]; then
        echo ""
    else
        echo "${args[@]}"
    fi
}

# Run the specified rover mode
run_rover_mode() {
    local python_args
    python_args=$(build_python_args)
    
    log_info "Starting Blue Rover in $ROVER_MODE mode..."
    log_debug "Python args: $python_args"
    
    case "$ROVER_MODE" in
        manual)
            log_info "Manual keyboard control mode"
            log_info "Controls: w/s (speed), a/d (steer), i/k/j/l (camera), t (photo), q (quit)"
            # Get IP address (handle different OS)
            local ip_addr
            if command -v hostname >/dev/null 2>&1 && hostname -I >/dev/null 2>&1; then
                ip_addr=$(hostname -I | awk '{print $1}')
            elif command -v ifconfig >/dev/null 2>&1; then
                ip_addr=$(ifconfig | grep -E 'inet [0-9]' | grep -v '127.0.0.1' | head -1 | awk '{print $2}')
            else
                ip_addr="localhost"
            fi
            log_info "Live video stream: http://${ip_addr}:8080/stream.mjpg"
            
            # Run manual control
            python src/blue_rover.py $python_args &
            echo $! > "$PID_FILE"
            ;;
            
        ps5)
            log_info "PS5 DualSense controller mode"
            log_info "Controls: L/R sticks, L2/R2 triggers, Square (stop), Options (quit)"
            
            # Run PS5 control
            python src/ps5_control.py $python_args &
            echo $! > "$PID_FILE"
            ;;
            
        monitor)
            log_info "Battery monitoring mode"
            log_info "Monitoring battery voltage with alerts..."
            
            # Run battery monitor
            python src/battery_monitor.py $python_args &
            echo $! > "$PID_FILE"
            ;;
            
        web)
            log_info "Web interface mode"
            log_info "Starting web server for browser-based control..."
            
            # Get IP address (handle different OS)
            local ip_addr
            if command -v hostname >/dev/null 2>&1 && hostname -I >/dev/null 2>&1; then
                ip_addr=$(hostname -I | awk '{print $1}')
            elif command -v ifconfig >/dev/null 2>&1; then
                ip_addr=$(ifconfig | grep -E 'inet [0-9]' | grep -v '127.0.0.1' | head -1 | awk '{print $2}')
            else
                ip_addr="localhost"
            fi
            
            log_info "Web interface: http://${ip_addr}:8000"
            log_info "Camera stream: http://${ip_addr}:8080/stream.mjpg"
            
            # Run web interface
            python src/web_interface.py $python_args &
            echo $! > "$PID_FILE"
            ;;
            
        *)
            log_error "Unknown mode: $ROVER_MODE"
            exit 1
            ;;
    esac
    
    # Wait for the process to start
    sleep 2
    
    # Check if process is still running
    local rover_pid
    rover_pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [[ -n "$rover_pid" ]] && kill -0 "$rover_pid" 2>/dev/null; then
        log_info "Rover started successfully (PID: $rover_pid)"
        log_info "Logs are being saved to: $LOG_DIR"
        
        # Wait for the process to complete
        wait "$rover_pid"
        local exit_code=$?
        
        # Clean up PID file
        rm -f "$PID_FILE"
        
        if [[ $exit_code -eq 0 ]]; then
            log_info "Rover stopped normally"
        else
            log_error "Rover exited with error code: $exit_code"
            exit $exit_code
        fi
    else
        log_error "Failed to start rover process"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# Display system status
show_status() {
    log_info "Blue Rover System Status"
    echo "=========================="
    echo "Mode: $ROVER_MODE"
    echo "Script Directory: $SCRIPT_DIR"
    echo "Virtual Environment: $VENV_DIR"
    echo "Log Directory: $LOG_DIR"
    echo "Debug Mode: $DEBUG_MODE"
    if [[ -n "$CONFIG_FILE" ]]; then
        echo "Configuration File: $CONFIG_FILE"
    fi
    echo "System: $(uname -a)"
    if [[ -f /proc/device-tree/model ]]; then
        echo "Hardware: $(cat /proc/device-tree/model)"
    fi
    echo "Python Version: $(python --version 2>&1)"
    echo "=========================="
}

# Main execution function
main() {
    # Parse command line arguments
    parse_arguments "$@"
    
    # Check system requirements
    check_requirements
    
    # Activate virtual environment
    activate_venv
    
    # Set up signal handlers for graceful shutdown
    setup_signal_handlers
    
    # Show system status if debug mode
    if [[ "$DEBUG_MODE" == "true" ]]; then
        show_status
    fi
    
    # Check hardware connectivity
    check_hardware
    
    # Run the specified rover mode
    run_rover_mode
}

# Execute main function with all arguments
main "$@"