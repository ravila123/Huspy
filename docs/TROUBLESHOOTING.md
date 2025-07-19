# Troubleshooting Guide

This guide covers common issues and their solutions for the Blue Rover system.

## Quick Diagnostics

### System Health Check
```bash
# Run comprehensive system check
./scripts/validate_hardware.sh

# Check service status
systemctl --user status blue-rover-battery
systemctl --user status blue-rover-camera

# View recent logs
journalctl --user -u blue-rover-battery --since "1 hour ago"
```

### Basic Connectivity Test
```bash
# Test camera
libcamera-hello --timeout 2000

# Test controller
jstest /dev/input/js0

# Test network
ping -c 4 8.8.8.8
```

## Installation Issues

### Setup Script Fails

**Problem**: `./setup.sh` exits with errors

**Common Causes & Solutions**:

1. **Permission Denied**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Missing Dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv git
   ./setup.sh
   ```

3. **Virtual Environment Creation Fails**:
   ```bash
   # Remove existing venv and retry
   rm -rf venv/
   python3 -m venv venv --system-site-packages
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **System Package Installation Issues**:
   ```bash
   # Update package lists
   sudo apt update
   
   # Fix broken packages
   sudo apt --fix-broken install
   
   # Clear package cache
   sudo apt clean && sudo apt autoclean
   ```

### Python Package Installation Problems

**Problem**: pip install fails with compilation errors

**Solutions**:
```bash
# Install build dependencies
sudo apt install build-essential python3-dev

# Use pre-compiled wheels when available
pip install --only-binary=all -r requirements.txt

# For specific packages that fail:
sudo apt install python3-opencv python3-numpy python3-pygame
```

### Permission Issues

**Problem**: Scripts can't access hardware or create files

**Solutions**:
```bash
# Add user to required groups
sudo usermod -a -G gpio,i2c,spi,video,audio $USER

# Set proper permissions for device files
sudo chmod 666 /dev/gpiomem
sudo chmod 666 /dev/i2c-*

# Logout and login again for group changes to take effect
```

## Hardware Connection Issues

### Camera Problems

**Problem**: Camera not detected or poor quality

**Diagnostics**:
```bash
# Check camera detection
libcamera-hello --list-cameras

# Test camera functionality
libcamera-still -o test.jpg
```

**Solutions**:

1. **Camera Not Detected**:
   - Check physical connection to camera port
   - Enable camera interface: `sudo raspi-config`
   - Reboot after enabling camera

2. **Poor Image Quality**:
   ```bash
   # Adjust camera settings
   libcamera-still -o test.jpg --width 1920 --height 1080 --quality 95
   ```

3. **Camera Stream Lag**:
   - Reduce resolution in configuration
   - Check network bandwidth
   - Lower frame rate if needed

### Controller Connection Issues

**Problem**: PS5 controller not connecting or responding

**Diagnostics**:
```bash
# Check Bluetooth status
sudo systemctl status bluetooth

# List paired devices
bluetoothctl devices

# Test controller input
jstest /dev/input/js0
```

**Solutions**:

1. **Controller Won't Pair**:
   ```bash
   # Reset Bluetooth service
   sudo systemctl restart bluetooth
   
   # Clear Bluetooth cache
   sudo rm -rf /var/lib/bluetooth/*
   sudo systemctl restart bluetooth
   
   # Re-pair controller
   sudo bluetoothctl
   scan on
   pair [MAC_ADDRESS]
   ```

2. **Controller Disconnects Frequently**:
   - Check controller battery level
   - Reduce distance from Pi
   - Check for interference sources
   - Update controller firmware if possible

3. **Wrong Button Mappings**:
   ```bash
   # Recalibrate controller
   jstest-gtk /dev/input/js0
   
   # Check controller type detection
   cat /proc/bus/input/devices
   ```

### Motor Control Problems

**Problem**: Motors not responding or erratic movement

**Diagnostics**:
```bash
# Check GPIO permissions
ls -l /dev/gpiomem

# Test GPIO functionality
gpio readall  # If wiringpi installed
```

**Solutions**:

1. **No Motor Response**:
   - Check power connections
   - Verify battery voltage (should be >6.5V)
   - Test motor drivers individually
   - Check GPIO pin assignments

2. **Erratic Movement**:
   - Check for loose connections
   - Verify adequate power supply
   - Reduce motor speeds for testing
   - Check for electromagnetic interference

3. **One Motor Not Working**:
   - Swap motor connections to isolate issue
   - Check individual motor with multimeter
   - Verify motor driver functionality

## Network and SSH Issues

### SSH Connection Problems

**Problem**: Cannot connect via SSH

**Diagnostics**:
```bash
# Check SSH service status
sudo systemctl status ssh

# Check network connectivity
ip addr show
ping [PI_IP_ADDRESS]
```

**Solutions**:

1. **SSH Service Not Running**:
   ```bash
   sudo systemctl enable ssh
   sudo systemctl start ssh
   ```

2. **Connection Refused**:
   - Check firewall settings: `sudo ufw status`
   - Verify SSH port (default 22): `sudo netstat -tlnp | grep :22`
   - Check SSH configuration: `sudo nano /etc/ssh/sshd_config`

3. **Key Authentication Fails**:
   ```bash
   # Check authorized_keys file
   cat ~/.ssh/authorized_keys
   
   # Fix permissions
   chmod 700 ~/.ssh
   chmod 600 ~/.ssh/authorized_keys
   ```

### WiFi Connection Issues

**Problem**: Unstable or slow WiFi connection

**Solutions**:

1. **Poor Signal Strength**:
   ```bash
   # Check signal strength
   iwconfig wlan0
   
   # Scan for networks
   sudo iwlist wlan0 scan | grep ESSID
   ```

2. **Frequent Disconnections**:
   ```bash
   # Disable power management
   sudo iwconfig wlan0 power off
   
   # Add to /etc/rc.local for persistence
   echo "iwconfig wlan0 power off" | sudo tee -a /etc/rc.local
   ```

3. **Slow Performance**:
   - Use 5GHz band if available
   - Check for interference
   - Position Pi closer to router
   - Consider external WiFi adapter

## Software Runtime Issues

### Service Startup Problems

**Problem**: Services fail to start automatically

**Diagnostics**:
```bash
# Check service status
systemctl --user status blue-rover-battery
systemctl --user status blue-rover-camera

# View service logs
journalctl --user -u blue-rover-battery -f
```

**Solutions**:

1. **Service Won't Start**:
   ```bash
   # Reload systemd configuration
   systemctl --user daemon-reload
   
   # Enable services
   systemctl --user enable blue-rover-battery
   systemctl --user enable blue-rover-camera
   ```

2. **Service Crashes on Startup**:
   - Check Python virtual environment path
   - Verify all dependencies installed
   - Check file permissions
   - Review error logs for specific issues

### Application Crashes

**Problem**: Blue Rover application crashes during operation

**Common Causes & Solutions**:

1. **Import Errors**:
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

2. **Hardware Access Errors**:
   ```bash
   # Check user groups
   groups $USER
   
   # Add to required groups if missing
   sudo usermod -a -G gpio,i2c,spi $USER
   ```

3. **Memory Issues**:
   ```bash
   # Check memory usage
   free -h
   
   # Check for memory leaks
   top -p $(pgrep python)
   ```

### Performance Issues

**Problem**: Slow response or high latency

**Solutions**:

1. **High CPU Usage**:
   ```bash
   # Check CPU usage
   htop
   
   # Reduce camera resolution
   # Lower control loop frequency
   # Disable unnecessary services
   ```

2. **Memory Leaks**:
   ```bash
   # Monitor memory usage over time
   watch -n 5 free -h
   
   # Restart services periodically if needed
   systemctl --user restart blue-rover-battery
   ```

3. **Network Latency**:
   - Use wired connection for testing
   - Reduce video stream quality
   - Optimize control packet size

## Recovery Procedures

### Complete System Reset

If all else fails, perform a complete reset:

```bash
# Stop all services
systemctl --user stop blue-rover-battery
systemctl --user stop blue-rover-camera

# Remove virtual environment
rm -rf venv/

# Clean up logs
rm -rf logs/*

# Re-run setup
./setup.sh
```

### Factory Reset

For a complete fresh start:

```bash
# Remove all Blue Rover files
cd ..
rm -rf blue-rover/

# Re-clone and setup
git clone https://github.com/your-username/blue-rover.git
cd blue-rover
./setup.sh
```

### Backup and Restore

**Create Backup**:
```bash
# Backup configuration and logs
tar -czf blue-rover-backup.tar.gz config/ logs/ venv/pyvenv.cfg
```

**Restore from Backup**:
```bash
# Extract backup
tar -xzf blue-rover-backup.tar.gz

# Reinstall if needed
./setup.sh
```

## Getting Help

### Log Collection

When reporting issues, collect relevant logs:

```bash
# System logs
sudo journalctl --since "1 hour ago" > system-logs.txt

# Service logs
journalctl --user -u blue-rover-battery --since "1 hour ago" > battery-logs.txt
journalctl --user -u blue-rover-camera --since "1 hour ago" > camera-logs.txt

# Hardware information
lsusb > hardware-info.txt
lscpu >> hardware-info.txt
free -h >> hardware-info.txt
```

### Diagnostic Information

Include this information when seeking help:

```bash
# System information
uname -a
cat /etc/os-release
python3 --version
pip --version

# Hardware detection
lsusb
lsblk
vcgencmd measure_temp
vcgencmd get_throttled
```

### Community Resources

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check docs/ directory for detailed guides
- **Hardware Guide**: Review HARDWARE.md for setup issues
- **Development Guide**: See DEVELOPMENT.md for code-related problems

### Emergency Procedures

**Immediate Safety**:
1. Disconnect battery power
2. Stop all running processes: `pkill -f blue_rover`
3. Check for overheating: `vcgencmd measure_temp`
4. Inspect for physical damage

**System Recovery**:
1. Boot Pi in safe mode if needed
2. Check filesystem: `sudo fsck /dev/mmcblk0p2`
3. Free up disk space if full: `sudo apt clean`
4. Update system: `sudo apt update && sudo apt upgrade`

Remember: When in doubt, start with the basics - power, connections, and permissions are the most common sources of issues.