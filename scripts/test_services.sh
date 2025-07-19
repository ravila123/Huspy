#!/bin/bash
#
# Blue Rover Service Testing Script
#
# Tests the systemd service configurations to ensure they work correctly
# before installation and deployment.
#
# Usage:
#   ./scripts/test_services.sh [service_name]
#
# Tests:
# - Service file syntax validation
# - Python module import testing
# - Configuration validation
# - Dry-run service testing
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
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

# Test service file syntax
test_service_syntax() {
    local service="$1"
    local service_file="$PROJECT_ROOT/config/systemd/${service}.service"
    
    log_info "Testing $service service file syntax..."
    
    if [[ ! -f "$service_file" ]]; then
        log_error "Service file not found: $service_file"
        return 1
    fi
    
    # Basic syntax checks
    if ! grep -q "^\[Unit\]" "$service_file"; then
        log_error "Missing [Unit] section in $service_file"
        return 1
    fi
    
    if ! grep -q "^\[Service\]" "$service_file"; then
        log_error "Missing [Service] section in $service_file"
        return 1
    fi
    
    if ! grep -q "^\[Install\]" "$service_file"; then
        log_error "Missing [Install] section in $service_file"
        return 1
    fi
    
    if ! grep -q "^ExecStart=" "$service_file"; then
        log_error "Missing ExecStart directive in $service_file"
        return 1
    fi
    
    log_success "$service service file syntax is valid"
    return 0
}

# Test Python module imports
test_python_modules() {
    local service="$1"
    
    log_info "Testing Python modules for $service service..."
    
    # Check if virtual environment exists
    if [[ ! -d "$PROJECT_ROOT/venv" ]]; then
        log_warning "Virtual environment not found. Run setup.sh first."
        return 1
    fi
    
    # Activate virtual environment
    source "$PROJECT_ROOT/venv/bin/activate"
    
    case "$service" in
        "blue-rover-battery")
            # Test battery monitor imports
            if python -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from src.battery_monitor import BatteryMonitor, BatteryConfig
    print('Battery monitor imports successful')
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
" 2>/dev/null; then
                log_success "Battery monitor Python modules are available"
            else
                log_error "Battery monitor Python modules failed to import"
                return 1
            fi
            ;;
            
        "blue-rover-camera")
            # Test camera stream imports
            if python -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from src.camera_stream import CameraStreamService, CameraConfig
    print('Camera stream imports successful')
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
" 2>/dev/null; then
                log_success "Camera stream Python modules are available"
            else
                log_error "Camera stream Python modules failed to import"
                return 1
            fi
            ;;
    esac
    
    deactivate
    return 0
}

# Test service configuration
test_service_config() {
    local service="$1"
    local service_file="$PROJECT_ROOT/config/systemd/${service}.service"
    
    log_info "Testing $service service configuration..."
    
    # Create a temporary service file with substituted variables
    local temp_service="/tmp/${service}-test.service"
    sed "s|%h|$HOME|g; s|%i|$USER|g" "$service_file" > "$temp_service"
    
    # Check if systemd can parse the service file
    if command -v systemd-analyze >/dev/null 2>&1; then
        if systemd-analyze verify "$temp_service" 2>/dev/null; then
            log_success "$service service configuration is valid"
        else
            log_warning "$service service configuration has warnings (may still work)"
        fi
    else
        log_info "systemd-analyze not available, skipping detailed validation"
    fi
    
    # Check if ExecStart path exists
    local exec_start=$(grep "^ExecStart=" "$temp_service" | cut -d'=' -f2-)
    local python_path=$(echo "$exec_start" | awk '{print $1}')
    
    if [[ -f "$python_path" ]]; then
        log_success "Python executable path is valid: $python_path"
    else
        log_warning "Python executable not found: $python_path (run setup.sh first)"
    fi
    
    rm -f "$temp_service"
    return 0
}

# Dry run service test
test_service_dry_run() {
    local service="$1"
    
    log_info "Performing dry-run test for $service service..."
    
    # Check if virtual environment exists
    if [[ ! -d "$PROJECT_ROOT/venv" ]]; then
        log_warning "Virtual environment not found. Cannot perform dry-run test."
        return 1
    fi
    
    # Activate virtual environment
    source "$PROJECT_ROOT/venv/bin/activate"
    
    case "$service" in
        "blue-rover-battery")
            # Test battery monitor with --help flag
            if timeout 5 python -m src.battery_monitor --help >/dev/null 2>&1; then
                log_success "Battery monitor service can start (help test passed)"
            else
                log_error "Battery monitor service failed help test"
                deactivate
                return 1
            fi
            ;;
            
        "blue-rover-camera")
            # Test camera stream with --help flag
            if timeout 5 python -m src.camera_stream --help >/dev/null 2>&1; then
                log_success "Camera stream service can start (help test passed)"
            else
                log_error "Camera stream service failed help test"
                deactivate
                return 1
            fi
            ;;
    esac
    
    deactivate
    return 0
}

# Test individual service
test_service() {
    local service="$1"
    local failed=0
    
    echo -e "${BLUE}=== Testing $service Service ===${NC}"
    
    test_service_syntax "$service" || failed=1
    test_python_modules "$service" || failed=1
    test_service_config "$service" || failed=1
    test_service_dry_run "$service" || failed=1
    
    if [[ $failed -eq 0 ]]; then
        log_success "$service service tests passed"
    else
        log_error "$service service tests failed"
    fi
    
    echo
    return $failed
}

# Test all services
test_all_services() {
    local total_failed=0
    
    log_info "Testing all Blue Rover systemd services..."
    echo
    
    for service in "${SERVICES[@]}"; do
        test_service "$service" || total_failed=$((total_failed + 1))
    done
    
    if [[ $total_failed -eq 0 ]]; then
        log_success "All service tests passed!"
    else
        log_error "$total_failed service(s) failed testing"
    fi
    
    return $total_failed
}

# Show help
show_help() {
    cat << EOF
Blue Rover Service Testing Script

USAGE:
    $0 [service_name]

ARGUMENTS:
    service_name    Test specific service (optional)
                   Available: ${SERVICES[*]}

TESTS PERFORMED:
    - Service file syntax validation
    - Python module import testing
    - Service configuration validation
    - Dry-run service testing

EXAMPLES:
    $0                           # Test all services
    $0 blue-rover-battery        # Test battery service only
    $0 blue-rover-camera         # Test camera service only

EOF
}

# Main function
main() {
    cd "$PROJECT_ROOT"
    
    if [[ $# -eq 0 ]]; then
        test_all_services
    elif [[ $# -eq 1 ]]; then
        local service="$1"
        if [[ " ${SERVICES[*]} " =~ " ${service} " ]]; then
            test_service "$service"
        else
            log_error "Unknown service: $service"
            log_info "Available services: ${SERVICES[*]}"
            exit 1
        fi
    else
        show_help
        exit 1
    fi
}

# Run main function with all arguments
main "$@"