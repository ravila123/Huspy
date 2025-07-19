#!/bin/bash
# install_deps.sh - Blue Rover dependency installation script
# Handles Python packages in virtual environment and system dependencies

set -e  # Exit on any error

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

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PROJECT_ROOT/venv"
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"

log_info "Starting Blue Rover dependency installation..."
log_info "Project root: $PROJECT_ROOT"
log_info "Virtual environment: $VENV_PATH"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    log_error "Virtual environment not found at $VENV_PATH"
    log_error "Please run setup.sh first to create the virtual environment"
    exit 1
fi

# Check if requirements.txt exists
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    log_error "Requirements file not found at $REQUIREMENTS_FILE"
    exit 1
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Verify virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    log_error "Failed to activate virtual environment"
    exit 1
fi

log_success "Virtual environment activated: $VIRTUAL_ENV"

# Function to check if system package is installed
check_system_package() {
    local package=$1
    if dpkg -l | grep -q "^ii  $package "; then
        return 0
    else
        return 1
    fi
}

# Function to install system packages
install_system_packages() {
    log_info "Checking system dependencies..."
    
    local packages_needed=()
    local system_packages=(
        "python3-dev"           # Python development headers
        "python3-pip"           # Python package installer
        "python3-venv"          # Virtual environment support
        "libopencv-dev"         # OpenCV development libraries
        "python3-opencv"        # OpenCV Python bindings (system)
        "libjpeg-dev"           # JPEG library for image processing
        "libpng-dev"            # PNG library for image processing
        "libv4l-dev"            # Video4Linux development
        "v4l-utils"             # Video4Linux utilities
        "bluetooth"             # Bluetooth support
        "bluez"                 # Bluetooth protocol stack
        "libbluetooth-dev"      # Bluetooth development libraries
        "python3-bluez"         # Python Bluetooth bindings
        "i2c-tools"             # I2C utilities for GPIO
        "python3-smbus"         # I2C Python bindings
        "git"                   # Version control (may be needed for some packages)
        "build-essential"       # Compilation tools
        "cmake"                 # Build system (needed for some Python packages)
        "pkg-config"            # Package configuration tool
    )
    
    # Check which packages are missing
    for package in "${system_packages[@]}"; do
        if ! check_system_package "$package"; then
            packages_needed+=("$package")
        fi
    done
    
    if [ ${#packages_needed[@]} -gt 0 ]; then
        log_warning "The following system packages are missing:"
        printf '  %s\n' "${packages_needed[@]}"
        
        read -p "Install missing system packages? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "Installing system packages..."
            sudo apt-get update
            sudo apt-get install -y "${packages_needed[@]}"
            log_success "System packages installed successfully"
        else
            log_warning "Skipping system package installation"
            log_warning "Some Python packages may fail to install without these dependencies"
        fi
    else
        log_success "All required system packages are already installed"
    fi
}

# Function to upgrade pip and install wheel
upgrade_pip() {
    log_info "Upgrading pip and installing build tools..."
    
    # Upgrade pip to latest version
    python -m pip install --upgrade pip
    
    # Install wheel and setuptools for better package building
    python -m pip install --upgrade wheel setuptools
    
    log_success "Pip and build tools upgraded successfully"
}

# Function to handle pip conflicts and retries
install_python_packages() {
    log_info "Installing Python packages from requirements.txt..."
    
    local max_retries=3
    local retry_count=0
    local install_success=false
    
    while [ $retry_count -lt $max_retries ] && [ "$install_success" = false ]; do
        retry_count=$((retry_count + 1))
        log_info "Installation attempt $retry_count of $max_retries..."
        
        if python -m pip install -r "$REQUIREMENTS_FILE"; then
            install_success=true
            log_success "Python packages installed successfully"
        else
            log_warning "Installation attempt $retry_count failed"
            
            if [ $retry_count -lt $max_retries ]; then
                log_info "Trying alternative installation strategies..."
                
                # Try installing packages one by one to isolate conflicts
                log_info "Attempting individual package installation..."
                while IFS= read -r line; do
                    # Skip empty lines and comments
                    if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
                        package=$(echo "$line" | sed 's/[[:space:]]*#.*//')  # Remove inline comments
                        if [[ -n "$package" ]]; then
                            log_info "Installing: $package"
                            if ! python -m pip install "$package"; then
                                log_warning "Failed to install $package, continuing with others..."
                            fi
                        fi
                    fi
                done < "$REQUIREMENTS_FILE"
                
                # Check if this resolved the issues
                if python -m pip check; then
                    install_success=true
                    log_success "Individual package installation completed successfully"
                fi
            fi
        fi
    done
    
    if [ "$install_success" = false ]; then
        log_error "Failed to install Python packages after $max_retries attempts"
        return 1
    fi
}

# Function to validate installation
validate_installation() {
    log_info "Validating Python package installation..."
    
    # Check for dependency conflicts
    if python -m pip check; then
        log_success "No dependency conflicts detected"
    else
        log_warning "Dependency conflicts detected, but installation may still work"
    fi
    
    # Test critical imports
    log_info "Testing critical package imports..."
    
    local test_imports=(
        "picarx"
        "vilib"
        "readchar"
        "pydualsense"
        "bleak"
        "paho.mqtt.client"
        "cv2"
        "ultralytics"
    )
    
    local failed_imports=()
    
    for import_name in "${test_imports[@]}"; do
        if python -c "import $import_name" 2>/dev/null; then
            log_success "✓ $import_name"
        else
            log_error "✗ $import_name"
            failed_imports+=("$import_name")
        fi
    done
    
    if [ ${#failed_imports[@]} -eq 0 ]; then
        log_success "All critical packages imported successfully"
        return 0
    else
        log_error "Failed to import the following packages:"
        printf '  %s\n' "${failed_imports[@]}"
        return 1
    fi
}

# Function to create validation report
create_validation_report() {
    local report_file="$PROJECT_ROOT/logs/dependency_validation.log"
    
    # Create logs directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/logs"
    
    log_info "Creating dependency validation report..."
    
    {
        echo "Blue Rover Dependency Validation Report"
        echo "========================================"
        echo "Date: $(date)"
        echo "Virtual Environment: $VIRTUAL_ENV"
        echo ""
        
        echo "Python Version:"
        python --version
        echo ""
        
        echo "Pip Version:"
        python -m pip --version
        echo ""
        
        echo "Installed Packages:"
        python -m pip list
        echo ""
        
        echo "Dependency Check:"
        python -m pip check || echo "Conflicts detected (see above)"
        echo ""
        
        echo "System Packages (relevant):"
        dpkg -l | grep -E "(python3|opencv|bluetooth|bluez|i2c|v4l)" || echo "No relevant system packages found"
        
    } > "$report_file"
    
    log_success "Validation report saved to: $report_file"
}

# Main execution
main() {
    # Install system dependencies
    install_system_packages
    
    # Upgrade pip and install build tools
    upgrade_pip
    
    # Install Python packages
    if ! install_python_packages; then
        log_error "Python package installation failed"
        exit 1
    fi
    
    # Validate installation
    if validate_installation; then
        log_success "All dependencies installed and validated successfully"
    else
        log_warning "Some packages failed validation but installation completed"
        log_warning "Check the validation report for details"
    fi
    
    # Create validation report
    create_validation_report
    
    log_success "Dependency installation completed!"
    log_info "Virtual environment is ready at: $VENV_PATH"
    log_info "To activate manually: source $VENV_PATH/bin/activate"
}

# Run main function
main "$@"