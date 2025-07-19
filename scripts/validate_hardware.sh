#!/bin/bash
#
# validate_hardware.sh
# ====================
# Hardware validation and testing script for Blue Rover system
# Tests PicarX connectivity, camera functionality, PS5 controller pairing,
# and provides comprehensive system status reporting.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Logging
LOG_DIR="$(dirname "$0")/../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/hardware_validation_$(date +%Y%m%d_%H%M%S).log"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1" | tee -a "$LOG_FILE"
    ((TESTS_PASSED++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1" | tee -a "$LOG_FILE"
    ((TESTS_FAILED++))
}

run_test() {
    local test_name="$1"
    local test_function="$2"
    
    ((TESTS_TOTAL++))
    log_info "Running test: $test_name"
    
    if $test_function; then
        log_success "$test_name"
        return 0
    else
        log_error "$test_name"
        return 1
    fi
}

# System information gathering
get_system_info() {
    log_info "=== SYSTEM INFORMATION ==="
    
    # Raspberry Pi model
    if [ -f /proc/device-tree/model ]; then
        PI_MODEL=$(cat /proc/device-tree/model)
        log_info "Raspberry Pi Model: $PI_MODEL"
    else
        log_warning "Could not detect Raspberry Pi model"
    fi
    
    # OS Information
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log_info "OS: $PRETTY_NAME"
    fi
    
    # Python version
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        log_info "Python: $PYTHON_VERSION"
    else
        log_error "Python3 not found"
    fi
    
    # Memory and CPU
    log_info "Memory: $(free -h | grep '^Mem:' | awk '{print $2}') total, $(free -h | grep '^Mem:' | awk '{print $7}') available"
    log_info "CPU: $(nproc) cores, $(cat /proc/loadavg | cut -d' ' -f1-3) load average"
    
    # Disk space
    log_info "Disk usage: $(df -h / | tail -1 | awk '{print $5}') used of $(df -h / | tail -1 | awk '{print $2}')"
    
    echo "" | tee -a "$LOG_FILE"
}

# Test virtual environment
test_virtual_environment() {
    local venv_path="$(dirname "$0")/../venv"
    
    if [ ! -d "$venv_path" ]; then
        log_error "Virtual environment not found at $venv_path"
        return 1
    fi
    
    if [ ! -f "$venv_path/bin/activate" ]; then
        log_error "Virtual environment activation script not found"
        return 1
    fi
    
    # Test activation
    source "$venv_path/bin/activate"
    if [ "$VIRTUAL_ENV" != "$(realpath "$venv_path")" ]; then
        log_error "Virtual environment activation failed"
        return 1
    fi
    
    log_success "Virtual environment found and functional"
    return 0
}

# Test Python dependencies
test_python_dependencies() {
    local venv_path="$(dirname "$0")/../venv"
    source "$venv_path/bin/activate"
    
    local required_packages=("picarx" "vilib" "readchar" "pydualsense")
    local missing_packages=()
    
    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -eq 0 ]; then
        log_success "All required Python packages are installed"
        return 0
    else
        log_error "Missing Python packages: ${missing_packages[*]}"
        log_info "Run 'pip install ${missing_packages[*]}' to install missing packages"
        return 1
    fi
}

# Test PicarX hardware connectivity
test_picarx_connectivity() {
    local venv_path="$(dirname "$0")/../venv"
    source "$venv_path/bin/activate"
    
    # Create a temporary test script
    local test_script="/tmp/test_picarx.py"
    cat > "$test_script" << 'EOF'
#!/usr/bin/env python3
import sys
import time
try:
    from picarx import Picarx
    px = Picarx()
    
    # Test basic initialization
    print("PicarX initialized successfully")
    
    # Test servo control (safe movements)
    px.set_dir_servo_angle(0)
    time.sleep(0.1)
    px.set_cam_pan_angle(0)
    time.sleep(0.1)
    px.set_cam_tilt_angle(0)
    time.sleep(0.1)
    
    # Test battery voltage reading
    try:
        voltage = px.get_battery_voltage()
        if voltage is not None:
            print(f"Battery voltage: {voltage}V")
        else:
            print("Battery voltage: Unable to read")
    except Exception as e:
        print(f"Battery voltage error: {e}")
    
    print("PicarX hardware test completed successfully")
    sys.exit(0)
    
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Hardware error: {e}")
    sys.exit(1)
EOF
    
    # Run the test
    if timeout 10 python3 "$test_script" 2>&1 | tee -a "$LOG_FILE"; then
        rm -f "$test_script"
        log_success "PicarX hardware connectivity test passed"
        return 0
    else
        rm -f "$test_script"
        log_error "PicarX hardware connectivity test failed"
        log_info "Check hardware connections and ensure Robot HAT is properly connected"
        return 1
    fi
}

# Test camera functionality
test_camera_functionality() {
    local venv_path="$(dirname "$0")/../venv"
    source "$venv_path/bin/activate"
    
    # Check if camera is detected by the system
    if ! ls /dev/video* &>/dev/null; then
        log_error "No camera devices found in /dev/"
        log_info "Enable camera interface: sudo raspi-config -> Interface Options -> Camera"
        return 1
    fi
    
    # Create a temporary camera test script
    local test_script="/tmp/test_camera.py"
    cat > "$test_script" << 'EOF'
#!/usr/bin/env python3
import sys
import time
try:
    from vilib import Vilib
    
    # Test camera initialization
    Vilib.camera_start(vflip=False, hflip=False)
    time.sleep(2)  # Allow camera to initialize
    
    # Test frame capture
    frame = Vilib.camera_capture()
    if frame is not None:
        print("Camera frame captured successfully")
        print(f"Frame size: {frame.size}")
    else:
        print("Failed to capture camera frame")
        sys.exit(1)
    
    # Test camera streaming capability
    Vilib.display(local=False, web=False)  # Don't start actual streaming
    
    Vilib.camera_close()
    print("Camera test completed successfully")
    sys.exit(0)
    
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Camera error: {e}")
    sys.exit(1)
EOF
    
    # Run the test
    if timeout 15 python3 "$test_script" 2>&1 | tee -a "$LOG_FILE"; then
        rm -f "$test_script"
        log_success "Camera functionality test passed"
        return 0
    else
        rm -f "$test_script"
        log_error "Camera functionality test failed"
        log_info "Check camera connection and ensure it's enabled in raspi-config"
        return 1
    fi
}

# Test PS5 controller connectivity
test_ps5_controller() {
    local venv_path="$(dirname "$0")/../venv"
    source "$venv_path/bin/activate"
    
    # Create a temporary PS5 controller test script
    local test_script="/tmp/test_ps5.py"
    cat > "$test_script" << 'EOF'
#!/usr/bin/env python3
import sys
import time
try:
    from pydualsense import pydualsense
    
    # Test controller detection
    ds = pydualsense()
    ds.init()
    
    if ds.connected():
        print("PS5 DualSense controller connected successfully")
        print(f"Controller battery: {ds.battery}%")
        
        # Test basic functionality
        ds.setLightbar(255, 0, 0)  # Red light
        time.sleep(0.5)
        ds.setLightbar(0, 255, 0)  # Green light
        time.sleep(0.5)
        ds.setLightbar(0, 0, 0)    # Turn off
        
        ds.close()
        print("PS5 controller test completed successfully")
        sys.exit(0)
    else:
        print("PS5 DualSense controller not found")
        print("Pair controller via Bluetooth or connect via USB-C")
        sys.exit(1)
        
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Controller error: {e}")
    sys.exit(1)
EOF
    
    # Run the test
    if timeout 10 python3 "$test_script" 2>&1 | tee -a "$LOG_FILE"; then
        rm -f "$test_script"
        log_success "PS5 controller connectivity test passed"
        return 0
    else
        rm -f "$test_script"
        log_warning "PS5 controller not connected or not paired"
        log_info "To pair PS5 controller:"
        log_info "1. Hold PS + Share buttons until light flashes"
        log_info "2. Run: sudo bluetoothctl"
        log_info "3. scan on, pair <MAC>, trust <MAC>, connect <MAC>"
        return 1
    fi
}

# Test system services
test_system_services() {
    local services=("bluetooth" "ssh")
    local service_status=0
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log_success "Service $service is running"
        else
            log_warning "Service $service is not running"
            log_info "Start with: sudo systemctl start $service"
            service_status=1
        fi
    done
    
    # Check for Blue Rover specific services (may not exist yet)
    local rover_services=("blue-rover-battery" "blue-rover-camera")
    for service in "${rover_services[@]}"; do
        if systemctl --user list-unit-files | grep -q "$service"; then
            if systemctl --user is-active --quiet "$service"; then
                log_success "User service $service is running"
            else
                log_info "User service $service exists but not running"
            fi
        else
            log_info "User service $service not installed (this is normal for fresh setup)"
        fi
    done
    
    return $service_status
}

# Test network connectivity
test_network_connectivity() {
    # Test local network
    if ping -c 1 -W 5 8.8.8.8 &>/dev/null; then
        log_success "Internet connectivity available"
    else
        log_warning "No internet connectivity"
        log_info "Check WiFi/Ethernet connection"
    fi
    
    # Test SSH daemon
    if systemctl is-active --quiet ssh; then
        SSH_PORT=$(grep -E "^Port" /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}' || echo "22")
        log_success "SSH daemon is running on port $SSH_PORT"
    else
        log_error "SSH daemon is not running"
        log_info "Start with: sudo systemctl start ssh"
        return 1
    fi
    
    return 0
}

# Generate diagnostic report
generate_diagnostic_report() {
    log_info "=== DIAGNOSTIC REPORT ==="
    
    # Hardware information
    log_info "Hardware Information:"
    if command -v vcgencmd &> /dev/null; then
        TEMP=$(vcgencmd measure_temp | cut -d'=' -f2)
        log_info "  CPU Temperature: $TEMP"
        
        THROTTLED=$(vcgencmd get_throttled)
        if [ "$THROTTLED" = "throttled=0x0" ]; then
            log_info "  Throttling: None"
        else
            log_warning "  Throttling detected: $THROTTLED"
        fi
    fi
    
    # GPIO status
    if command -v gpio &> /dev/null; then
        log_info "GPIO utility available"
    else
        log_info "GPIO utility not installed (wiringpi)"
    fi
    
    # I2C devices
    if command -v i2cdetect &> /dev/null; then
        log_info "I2C devices detected:"
        i2cdetect -y 1 2>/dev/null | tee -a "$LOG_FILE" || log_info "  No I2C devices or permission denied"
    else
        log_info "I2C tools not installed"
    fi
    
    # USB devices
    log_info "USB devices:"
    lsusb 2>/dev/null | tee -a "$LOG_FILE" || log_info "  Unable to list USB devices"
    
    # Bluetooth devices
    if command -v bluetoothctl &> /dev/null; then
        log_info "Paired Bluetooth devices:"
        timeout 5 bluetoothctl paired-devices 2>/dev/null | tee -a "$LOG_FILE" || log_info "  No paired devices or timeout"
    fi
    
    echo "" | tee -a "$LOG_FILE"
}

# Main execution
main() {
    echo "Blue Rover Hardware Validation Script" | tee "$LOG_FILE"
    echo "====================================" | tee -a "$LOG_FILE"
    echo "Started at: $(date)" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
    
    # System information
    get_system_info
    
    # Run all tests
    log_info "=== RUNNING HARDWARE TESTS ==="
    
    run_test "Virtual Environment" test_virtual_environment
    run_test "Python Dependencies" test_python_dependencies
    run_test "PicarX Connectivity" test_picarx_connectivity
    run_test "Camera Functionality" test_camera_functionality
    run_test "PS5 Controller" test_ps5_controller
    run_test "System Services" test_system_services
    run_test "Network Connectivity" test_network_connectivity
    
    # Generate diagnostic report
    generate_diagnostic_report
    
    # Summary
    echo "" | tee -a "$LOG_FILE"
    log_info "=== TEST SUMMARY ==="
    log_info "Total tests: $TESTS_TOTAL"
    log_success "Passed: $TESTS_PASSED"
    log_error "Failed: $TESTS_FAILED"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        log_success "All hardware validation tests passed!"
        echo -e "${GREEN}✓ Blue Rover system is ready for operation${NC}" | tee -a "$LOG_FILE"
    else
        log_warning "Some tests failed. Check the diagnostic information above."
        echo -e "${YELLOW}⚠ Blue Rover system has issues that need attention${NC}" | tee -a "$LOG_FILE"
    fi
    
    echo "" | tee -a "$LOG_FILE"
    log_info "Full log saved to: $LOG_FILE"
    echo "Completed at: $(date)" | tee -a "$LOG_FILE"
    
    # Exit with appropriate code
    if [ $TESTS_FAILED -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# Script entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi