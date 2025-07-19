#!/bin/bash

# Blue Rover Setup Script
# Automated setup for Raspberry Pi deployment with environment detection

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LOG_FILE="$SCRIPT_DIR/setup.log"
PYTHON_CMD=""
SYSTEM_PACKAGES_NEEDED=()
SETUP_FAILED=false

# Logging functions
log() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1" | tee -a "$LOG_FILE"
}

# Error handling function
handle_error() {
    local exit_code=$?
    local line_number=$1
    error "Setup failed at line $line_number with exit code $exit_code"
    SETUP_FAILED=true
    cleanup_on_failure
    exit $exit_code
}

# Set up error trap
trap 'handle_error $LINENO' ERR

# Handle interruption (Ctrl+C)
handle_interrupt() {
    echo ""
    warn "Setup interrupted by user"
    SETUP_FAILED=true
    cleanup_on_failure
    exit 130
}

trap 'handle_interrupt' INT

# Cleanup function for failed setups
cleanup_on_failure() {
    warn "Cleaning up after failed setup..."
    if [ -d "$VENV_DIR" ]; then
        warn "Removing incomplete virtual environment..."
        rm -rf "$VENV_DIR"
    fi
    error "Setup failed. Check $LOG_FILE for details."
    echo ""
    echo "To retry setup:"
    echo "1. Fix any issues mentioned above"
    echo "2. Run: ./setup.sh"
    echo ""
    echo "For help, check docs/TROUBLESHOOTING.md"
}

# Success cleanup
cleanup_on_success() {
    log "Setup completed successfully!"
    echo ""
    echo -e "${GREEN}✓ Blue Rover setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Connect your hardware (PicarX, camera, PS5 controller)"
    echo "2. Run hardware validation: ./scripts/validate_hardware.sh"
    echo "3. Start the rover: ./run_rover.sh [mode]"
    echo ""
    echo "Available modes:"
    echo "  - ps5: PS5 controller control"
    echo "  - manual: Keyboard control"
    echo "  - web: Web interface"
    echo "  - monitor: Battery monitoring only"
    echo ""
    echo "For remote access, configure SSH keys and connect via SSH."
}

# Detect system information
detect_system() {
    log "Detecting system environment..."
    
    # Detect OS
    local OS_NAME="Unknown"
    local OS_VERSION="Unknown"
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME="$NAME"
        OS_VERSION="$VERSION"
        debug "OS: $OS_NAME $OS_VERSION"
        
        # Check if running on Raspberry Pi OS
        if [[ "$NAME" == *"Raspberry Pi"* ]] || [[ "$ID" == "raspbian" ]]; then
            log "Detected Raspberry Pi OS: $VERSION_ID"
        else
            warn "Not running on Raspberry Pi OS. Some features may not work correctly."
            warn "Detected OS: $OS_NAME $OS_VERSION"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS_NAME="macOS"
        OS_VERSION=$(sw_vers -productVersion 2>/dev/null || echo "Unknown")
        warn "Running on macOS - this setup is designed for Raspberry Pi OS"
        debug "OS: $OS_NAME $OS_VERSION"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS_NAME="Linux"
        warn "Could not detect specific Linux distribution"
        debug "OS: $OS_NAME"
    else
        warn "Could not detect OS version"
        debug "OSTYPE: $OSTYPE"
    fi
    
    # Detect Raspberry Pi model (only on Linux)
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /proc/device-tree/model ]; then
            PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null)
            log "Raspberry Pi Model: $PI_MODEL"
        elif [ -f /proc/cpuinfo ]; then
            PI_MODEL=$(grep "Model" /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs)
            if [ -n "$PI_MODEL" ]; then
                log "Raspberry Pi Model: $PI_MODEL"
            else
                debug "Could not detect Raspberry Pi model from /proc/cpuinfo"
            fi
        fi
    fi
    
    # Detect architecture
    ARCH=$(uname -m)
    debug "Architecture: $ARCH"
    
    # Check available memory (Linux only)
    if [ -f /proc/meminfo ]; then
        MEMORY_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
        MEMORY_MB=$((MEMORY_KB / 1024))
        debug "Available memory: ${MEMORY_MB}MB"
        
        if [ $MEMORY_MB -lt 512 ]; then
            warn "Low memory detected (${MEMORY_MB}MB). Performance may be limited."
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS memory detection
        MEMORY_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
        MEMORY_MB=$((MEMORY_BYTES / 1024 / 1024))
        debug "Available memory: ${MEMORY_MB}MB"
    else
        warn "Could not detect available memory"
    fi
}

# Detect Python version and set command
detect_python() {
    log "Detecting Python installation..."
    
    # Try different Python commands in order of preference
    local python_candidates=("python3.11" "python3.10" "python3.9" "python3.8" "python3" "python")
    
    for cmd in "${python_candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            local version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
            local major=$(echo $version | cut -d. -f1)
            local minor=$(echo $version | cut -d. -f2)
            
            debug "Found $cmd: Python $version"
            
            # Check if version is supported (Python 3.8+)
            if [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; then
                PYTHON_CMD="$cmd"
                log "Using Python $version ($cmd)"
                break
            else
                warn "$cmd version $version is too old (need Python 3.8+)"
            fi
        fi
    done
    
    if [ -z "$PYTHON_CMD" ]; then
        error "No suitable Python version found. Need Python 3.8 or higher."
        error "Please install Python 3.8+ and try again."
        return 1
    fi
    
    # Check if pip is available
    if ! $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
        error "pip is not available for $PYTHON_CMD"
        error "Please install pip: sudo apt update && sudo apt install python3-pip"
        return 1
    fi
    
    # Check if venv module is available
    if ! $PYTHON_CMD -m venv --help >/dev/null 2>&1; then
        warn "venv module not available, will try to install python3-venv"
        SYSTEM_PACKAGES_NEEDED+=("python3-venv")
    fi
}

# Check system dependencies
check_system_dependencies() {
    log "Checking system dependencies..."
    
    # Only check packages on Linux systems with apt
    if command -v dpkg >/dev/null 2>&1 && command -v apt >/dev/null 2>&1; then
        local packages_to_check=(
            "git"
            "curl"
            "build-essential"
            "python3-dev"
            "libffi-dev"
            "libjpeg-dev"
            "zlib1g-dev"
            "libssl-dev"
            "libopencv-dev"
        )
        
        for package in "${packages_to_check[@]}"; do
            if ! dpkg -l 2>/dev/null | grep -q "^ii  $package "; then
                debug "System package needed: $package"
                SYSTEM_PACKAGES_NEEDED+=("$package")
            fi
        done
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - check for basic tools
        local tools_to_check=("git" "curl")
        for tool in "${tools_to_check[@]}"; do
            if ! command -v "$tool" >/dev/null 2>&1; then
                warn "$tool not found. Please install Xcode Command Line Tools: xcode-select --install"
            fi
        done
        log "macOS detected - skipping Linux package checks"
    else
        warn "Package manager not detected. Manual dependency installation may be required."
    fi
    
    # Check for camera support (Linux only)
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -e /dev/video0 ] || [ -e /dev/video1 ]; then
            log "Camera device detected"
        else
            warn "No camera device found. Camera features will be disabled."
        fi
        
        # Check for GPIO access
        if [ -e /dev/gpiomem ]; then
            log "GPIO access available"
        else
            warn "GPIO access not available. Hardware control may be limited."
        fi
    else
        debug "Skipping hardware checks on non-Linux system"
    fi
}

# Install system packages if needed
install_system_packages() {
    if [ ${#SYSTEM_PACKAGES_NEEDED[@]} -eq 0 ]; then
        log "All required system packages are already installed"
        return 0
    fi
    
    log "System packages needed: ${SYSTEM_PACKAGES_NEEDED[*]}"
    
    echo ""
    echo -e "${YELLOW}The following system packages need to be installed:${NC}"
    printf '%s\n' "${SYSTEM_PACKAGES_NEEDED[@]}"
    echo ""
    
    read -p "Install these packages? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Installing system packages..."
        
        # Update package list
        log "Updating package list..."
        if ! sudo apt update; then
            error "Failed to update package list"
            return 1
        fi
        
        # Install packages
        log "Installing packages: ${SYSTEM_PACKAGES_NEEDED[*]}"
        if ! sudo apt install -y "${SYSTEM_PACKAGES_NEEDED[@]}"; then
            error "Failed to install system packages"
            return 1
        fi
        
        log "System packages installed successfully"
    else
        warn "Skipping system package installation"
        warn "Some features may not work without required packages"
    fi
}

# Create virtual environment
create_virtual_environment() {
    log "Creating virtual environment..."
    
    if [ -d "$VENV_DIR" ]; then
        warn "Virtual environment already exists at $VENV_DIR"
        read -p "Remove existing virtual environment and create new one? (y/N): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log "Removing existing virtual environment..."
            rm -rf "$VENV_DIR"
        else
            log "Using existing virtual environment"
            return 0
        fi
    fi
    
    log "Creating new virtual environment with $PYTHON_CMD..."
    if ! $PYTHON_CMD -m venv "$VENV_DIR"; then
        error "Failed to create virtual environment"
        return 1
    fi
    
    log "Virtual environment created at $VENV_DIR"
}

# Activate virtual environment and install dependencies
install_python_dependencies() {
    log "Installing Python dependencies..."
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    log "Upgrading pip..."
    if ! python -m pip install --upgrade pip; then
        error "Failed to upgrade pip"
        return 1
    fi
    
    # Install wheel for better package compilation
    log "Installing wheel..."
    if ! python -m pip install wheel; then
        warn "Failed to install wheel, continuing anyway..."
    fi
    
    # Install requirements
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        log "Installing requirements from requirements.txt..."
        if ! python -m pip install -r "$SCRIPT_DIR/requirements.txt"; then
            error "Failed to install Python requirements"
            error "Check $LOG_FILE for details"
            return 1
        fi
    else
        warn "requirements.txt not found, skipping Python package installation"
    fi
    
    log "Python dependencies installed successfully"
}

# Create necessary directories
create_directories() {
    log "Creating project directories..."
    
    local dirs=("logs" "config" "scripts")
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$SCRIPT_DIR/$dir" ]; then
            mkdir -p "$SCRIPT_DIR/$dir"
            debug "Created directory: $dir"
        fi
    done
}

# Set up permissions
setup_permissions() {
    log "Setting up permissions..."
    
    # Make scripts executable
    local scripts=("run_rover.sh")
    
    for script in "${scripts[@]}"; do
        if [ -f "$SCRIPT_DIR/$script" ]; then
            chmod +x "$SCRIPT_DIR/$script"
            debug "Made executable: $script"
        fi
    done
    
    # Make scripts in scripts/ directory executable
    if [ -d "$SCRIPT_DIR/scripts" ]; then
        find "$SCRIPT_DIR/scripts" -name "*.sh" -exec chmod +x {} \;
        debug "Made scripts in scripts/ directory executable"
    fi
}

# Validate installation
validate_installation() {
    log "Validating installation..."
    
    # Check virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        error "Virtual environment not found"
        return 1
    fi
    
    # Check if we can activate venv and import key packages
    source "$VENV_DIR/bin/activate"
    
    local test_imports=("picarx" "readchar")
    
    for package in "${test_imports[@]}"; do
        if ! python -c "import $package" 2>/dev/null; then
            warn "Could not import $package - some features may not work"
        else
            debug "Successfully imported $package"
        fi
    done
    
    log "Installation validation completed"
}

# Main setup function
main() {
    echo -e "${BLUE}Blue Rover Setup Script${NC}"
    echo "======================="
    echo ""
    
    # Initialize log file
    echo "Setup started at $(date)" > "$LOG_FILE"
    
    # Run setup steps
    detect_system
    detect_python
    check_system_dependencies
    install_system_packages
    create_virtual_environment
    install_python_dependencies
    create_directories
    setup_permissions
    validate_installation
    
    # Success cleanup
    cleanup_on_success
}

# Run main function
main "$@"