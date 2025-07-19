#!/bin/bash

# SSH Configuration Automation Script for Blue Rover
# This script configures SSH for secure remote access with key-based authentication

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration variables
SSH_CONFIG_FILE="/etc/ssh/sshd_config"
SSH_CONFIG_BACKUP="/etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)"
CUSTOM_SSH_PORT=""
INSTALL_FAIL2BAN=false
USER_HOME="$HOME"
SSH_DIR="$USER_HOME/.ssh"
AUTHORIZED_KEYS="$SSH_DIR/authorized_keys"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "This script should not be run as root for security reasons."
        print_error "Please run as a regular user. The script will prompt for sudo when needed."
        exit 1
    fi
}

# Function to backup SSH config
backup_ssh_config() {
    print_status "Creating backup of SSH configuration..."
    if sudo cp "$SSH_CONFIG_FILE" "$SSH_CONFIG_BACKUP"; then
        print_status "SSH config backed up to: $SSH_CONFIG_BACKUP"
    else
        print_error "Failed to backup SSH configuration"
        exit 1
    fi
}

# Function to create SSH directory and set permissions
setup_ssh_directory() {
    print_status "Setting up SSH directory structure..."
    
    # Create .ssh directory if it doesn't exist
    if [[ ! -d "$SSH_DIR" ]]; then
        mkdir -p "$SSH_DIR"
        print_status "Created SSH directory: $SSH_DIR"
    fi
    
    # Set proper permissions
    chmod 700 "$SSH_DIR"
    
    # Create authorized_keys file if it doesn't exist
    if [[ ! -f "$AUTHORIZED_KEYS" ]]; then
        touch "$AUTHORIZED_KEYS"
        print_status "Created authorized_keys file"
    fi
    
    chmod 600 "$AUTHORIZED_KEYS"
    print_status "SSH directory permissions configured"
}

# Function to generate SSH key pair instructions
generate_key_instructions() {
    print_header "SSH Key Pair Setup Instructions"
    echo
    echo "To generate an SSH key pair on your LOCAL machine (not on the Pi):"
    echo
    echo "1. On your local computer, run:"
    echo "   ssh-keygen -t ed25519 -C \"your-email@example.com\""
    echo "   (or use RSA: ssh-keygen -t rsa -b 4096 -C \"your-email@example.com\")"
    echo
    echo "2. When prompted for file location, press Enter for default"
    echo "3. Set a strong passphrase when prompted"
    echo
    echo "4. Copy your PUBLIC key to this Pi:"
    echo "   ssh-copy-id $(whoami)@$(hostname -I | awk '{print $1}')"
    echo "   (or manually copy ~/.ssh/id_ed25519.pub content to $AUTHORIZED_KEYS)"
    echo
    echo "5. Test the connection:"
    echo "   ssh $(whoami)@$(hostname -I | awk '{print $1}')"
    echo
}

# Function to configure SSH daemon
configure_ssh_daemon() {
    print_status "Configuring SSH daemon for security..."
    
    # Create temporary config file
    local temp_config="/tmp/sshd_config_new"
    cp "$SSH_CONFIG_FILE" "$temp_config"
    
    # Configure key-based authentication
    if ! grep -q "^PubkeyAuthentication yes" "$temp_config"; then
        if grep -q "^#PubkeyAuthentication" "$temp_config"; then
            sed -i 's/^#PubkeyAuthentication.*/PubkeyAuthentication yes/' "$temp_config"
        else
            echo "PubkeyAuthentication yes" >> "$temp_config"
        fi
        print_status "Enabled public key authentication"
    fi
    
    # Disable password authentication
    if ! grep -q "^PasswordAuthentication no" "$temp_config"; then
        if grep -q "^PasswordAuthentication" "$temp_config"; then
            sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' "$temp_config"
        else
            echo "PasswordAuthentication no" >> "$temp_config"
        fi
        print_status "Disabled password authentication"
    fi
    
    # Disable root login
    if ! grep -q "^PermitRootLogin no" "$temp_config"; then
        if grep -q "^PermitRootLogin" "$temp_config"; then
            sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' "$temp_config"
        else
            echo "PermitRootLogin no" >> "$temp_config"
        fi
        print_status "Disabled root login"
    fi
    
    # Configure custom port if specified
    if [[ -n "$CUSTOM_SSH_PORT" ]]; then
        if grep -q "^Port" "$temp_config"; then
            sed -i "s/^Port.*/Port $CUSTOM_SSH_PORT/" "$temp_config"
        else
            sed -i "s/^#Port 22/Port $CUSTOM_SSH_PORT/" "$temp_config"
        fi
        print_status "Set custom SSH port to: $CUSTOM_SSH_PORT"
    fi
    
    # Additional security settings
    if ! grep -q "^Protocol 2" "$temp_config"; then
        echo "Protocol 2" >> "$temp_config"
    fi
    
    if ! grep -q "^PermitEmptyPasswords no" "$temp_config"; then
        if grep -q "^PermitEmptyPasswords" "$temp_config"; then
            sed -i 's/^PermitEmptyPasswords.*/PermitEmptyPasswords no/' "$temp_config"
        else
            echo "PermitEmptyPasswords no" >> "$temp_config"
        fi
    fi
    
    if ! grep -q "^ChallengeResponseAuthentication no" "$temp_config"; then
        if grep -q "^ChallengeResponseAuthentication" "$temp_config"; then
            sed -i 's/^ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' "$temp_config"
        else
            echo "ChallengeResponseAuthentication no" >> "$temp_config"
        fi
    fi
    
    # Apply the new configuration
    if sudo cp "$temp_config" "$SSH_CONFIG_FILE"; then
        print_status "SSH daemon configuration updated"
        rm "$temp_config"
    else
        print_error "Failed to update SSH configuration"
        rm "$temp_config"
        exit 1
    fi
}

# Function to install and configure fail2ban
setup_fail2ban() {
    if [[ "$INSTALL_FAIL2BAN" == "true" ]]; then
        print_status "Installing and configuring fail2ban..."
        
        # Install fail2ban
        if ! command -v fail2ban-server &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y fail2ban
            print_status "fail2ban installed"
        else
            print_status "fail2ban already installed"
        fi
        
        # Create fail2ban jail configuration
        local jail_config="/etc/fail2ban/jail.local"
        if [[ ! -f "$jail_config" ]]; then
            sudo tee "$jail_config" > /dev/null << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ${CUSTOM_SSH_PORT:-22}
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF
            print_status "fail2ban jail configuration created"
        fi
        
        # Enable and start fail2ban
        sudo systemctl enable fail2ban
        sudo systemctl restart fail2ban
        print_status "fail2ban service enabled and started"
    fi
}

# Function to test SSH configuration
test_ssh_config() {
    print_status "Testing SSH configuration..."
    
    if sudo sshd -t; then
        print_status "SSH configuration is valid"
        return 0
    else
        print_error "SSH configuration has errors"
        return 1
    fi
}

# Function to restart SSH service
restart_ssh_service() {
    print_status "Restarting SSH service..."
    
    if sudo systemctl restart ssh; then
        print_status "SSH service restarted successfully"
    else
        print_error "Failed to restart SSH service"
        print_warning "Restoring backup configuration..."
        sudo cp "$SSH_CONFIG_BACKUP" "$SSH_CONFIG_FILE"
        sudo systemctl restart ssh
        exit 1
    fi
}

# Function to display final instructions
show_final_instructions() {
    print_header "SSH Setup Complete!"
    echo
    print_status "SSH has been configured with the following security settings:"
    echo "  ✓ Public key authentication enabled"
    echo "  ✓ Password authentication disabled"
    echo "  ✓ Root login disabled"
    echo "  ✓ Empty passwords disabled"
    
    if [[ -n "$CUSTOM_SSH_PORT" ]]; then
        echo "  ✓ Custom SSH port: $CUSTOM_SSH_PORT"
    fi
    
    if [[ "$INSTALL_FAIL2BAN" == "true" ]]; then
        echo "  ✓ fail2ban installed and configured"
    fi
    
    echo
    print_warning "IMPORTANT: Before logging out, test SSH access in a new terminal:"
    
    local ip_address=$(hostname -I | awk '{print $1}')
    if [[ -n "$CUSTOM_SSH_PORT" ]]; then
        echo "  ssh -p $CUSTOM_SSH_PORT $(whoami)@$ip_address"
    else
        echo "  ssh $(whoami)@$ip_address"
    fi
    
    echo
    print_warning "If you cannot connect, the backup configuration is at:"
    echo "  $SSH_CONFIG_BACKUP"
    echo
    print_status "SSH setup completed successfully!"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -p, --port PORT     Set custom SSH port (default: 22)"
    echo "  -f, --fail2ban      Install and configure fail2ban"
    echo "  -h, --help          Show this help message"
    echo
    echo "Example:"
    echo "  $0 --port 2222 --fail2ban"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            CUSTOM_SSH_PORT="$2"
            shift 2
            ;;
        -f|--fail2ban)
            INSTALL_FAIL2BAN=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate custom port if specified
if [[ -n "$CUSTOM_SSH_PORT" ]]; then
    if ! [[ "$CUSTOM_SSH_PORT" =~ ^[0-9]+$ ]] || [[ "$CUSTOM_SSH_PORT" -lt 1024 ]] || [[ "$CUSTOM_SSH_PORT" -gt 65535 ]]; then
        print_error "Invalid port number. Please use a port between 1024 and 65535."
        exit 1
    fi
fi

# Main execution
main() {
    print_header "Blue Rover SSH Configuration Setup"
    echo
    
    # Check if not running as root
    check_root
    
    # Setup SSH directory
    setup_ssh_directory
    
    # Show key generation instructions
    generate_key_instructions
    
    # Ask user if they want to continue
    echo
    read -p "Have you set up your SSH keys and are ready to configure the SSH daemon? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Setup cancelled. Run this script again when you're ready."
        exit 0
    fi
    
    # Backup current SSH config
    backup_ssh_config
    
    # Configure SSH daemon
    configure_ssh_daemon
    
    # Test configuration
    if ! test_ssh_config; then
        print_error "SSH configuration test failed. Restoring backup..."
        sudo cp "$SSH_CONFIG_BACKUP" "$SSH_CONFIG_FILE"
        exit 1
    fi
    
    # Setup fail2ban if requested
    setup_fail2ban
    
    # Restart SSH service
    restart_ssh_service
    
    # Show final instructions
    show_final_instructions
}

# Run main function
main "$@"