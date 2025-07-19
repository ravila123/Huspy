# Hardware Requirements and Setup

This document outlines the hardware requirements and setup instructions for the Blue Rover system.

## Required Hardware

### Raspberry Pi
- **Recommended**: Raspberry Pi 4 Model B (4GB or 8GB RAM)
- **Minimum**: Raspberry Pi 3B+ or Pi Zero 2W
- **OS**: Raspberry Pi OS (Bullseye or Bookworm)
- **Storage**: 32GB+ microSD card (Class 10 or better)

### Robot Platform
- **Primary**: PicarX Robot Kit
- **Alternative**: Any robot platform with compatible motor drivers
- **Motors**: DC motors with encoder feedback (recommended)
- **Chassis**: Sturdy platform capable of carrying Pi and accessories

### Camera System
- **Recommended**: Raspberry Pi Camera Module v2 or v3
- **Alternative**: USB webcam (with reduced performance)
- **Mount**: Pan/tilt servo mount (2 servos)
- **Resolution**: 1080p capable for best streaming quality

### Controller
- **Primary**: Sony PS5 DualSense Controller
- **Connection**: Bluetooth or USB-C
- **Alternative**: Any Bluetooth gamepad with standard button mapping
- **Backup**: Keyboard control via SSH

### Power System
- **Battery**: 7.4V Li-Po battery (2S configuration)
- **Capacity**: 2200mAh minimum for 1+ hour operation
- **Connector**: XT60 or compatible
- **Monitoring**: Voltage divider circuit for battery monitoring

### Optional Components
- **WiFi**: Built-in Pi WiFi or USB WiFi adapter
- **Audio**: USB microphone/speaker for voice commands
- **Sensors**: Ultrasonic distance sensors, IMU, GPS module
- **Lighting**: LED strips or headlights for night operation

## Hardware Setup Instructions

### 1. Raspberry Pi Preparation

**Install Raspberry Pi OS**:
1. Download Raspberry Pi Imager
2. Flash Raspberry Pi OS (64-bit recommended) to microSD
3. Enable SSH in Pi Imager advanced options
4. Set username/password and WiFi credentials
5. Boot Pi and update system:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

**Enable Required Interfaces**:
```bash
sudo raspi-config
```
- Enable Camera interface
- Enable I2C interface
- Enable SPI interface (if using additional sensors)
- Enable GPIO remote access

### 2. PicarX Assembly

**Basic Assembly**:
1. Follow PicarX assembly instructions
2. Mount Raspberry Pi on designated platform
3. Connect camera to Pi camera port
4. Install camera on pan/tilt mount

**Wiring Connections**:
- **Power**: Connect battery to PicarX power distribution
- **Motors**: Ensure motor drivers are properly connected
- **Servos**: Connect steering and camera servos to designated pins
- **I2C**: Connect any I2C sensors to SDA/SCL pins

**Pin Assignments** (default PicarX configuration):
```
GPIO 2  (SDA)   - I2C Data
GPIO 3  (SCL)   - I2C Clock
GPIO 12         - Motor PWM A
GPIO 13         - Motor PWM B
GPIO 16         - Motor Direction A
GPIO 20         - Motor Direction B
GPIO 18         - Servo PWM (steering)
GPIO 19         - Servo PWM (camera pan)
GPIO 21         - Servo PWM (camera tilt)
```

### 3. Camera Setup

**Physical Installation**:
1. Mount camera module on pan/tilt servo assembly
2. Route camera cable carefully to avoid interference
3. Secure all connections and test servo movement
4. Ensure camera has clear field of view

**Camera Configuration**:
```bash
# Test camera functionality
libcamera-hello --timeout 5000

# Test video recording
libcamera-vid -t 10000 -o test.h264
```

### 4. Controller Pairing

**PS5 Controller Setup**:
1. Put controller in pairing mode (PS + Share buttons)
2. Pair via Bluetooth:
   ```bash
   sudo bluetoothctl
   scan on
   pair [CONTROLLER_MAC]
   trust [CONTROLLER_MAC]
   connect [CONTROLLER_MAC]
   ```

**Test Controller**:
```bash
# Install testing tools
sudo apt install jstest-gtk

# Test controller input
jstest /dev/input/js0
```

### 5. Power System Configuration

**Battery Monitoring Circuit**:
- Connect battery positive through voltage divider to ADC pin
- Use 10kΩ and 3.3kΩ resistors for 7.4V battery
- Connect to GPIO pin configured for analog reading

**Power Management**:
- Install low-voltage cutoff protection
- Configure automatic shutdown at low battery
- Set up charging circuit if using rechargeable battery

## Hardware Validation

### Pre-deployment Checklist

**Mechanical**:
- [ ] All screws and connections secure
- [ ] Wheels turn freely
- [ ] Steering mechanism operates smoothly
- [ ] Camera mount moves without binding
- [ ] No loose wires or components

**Electrical**:
- [ ] Battery voltage within normal range (7.0-8.4V for 2S Li-Po)
- [ ] All connections secure and properly insulated
- [ ] No short circuits or exposed conductors
- [ ] Power switch operates correctly
- [ ] Charging system functional (if applicable)

**Software Integration**:
- [ ] Pi boots successfully
- [ ] Camera detected and functional
- [ ] Controller pairs and responds
- [ ] Motor control responds to commands
- [ ] Battery monitoring reports correct voltage
- [ ] All services start automatically

### Testing Procedures

**Basic Functionality Test**:
```bash
# Run hardware validation script
./scripts/validate_hardware.sh
```

**Manual Testing**:
1. **Movement Test**: Verify forward/backward/steering
2. **Camera Test**: Check pan/tilt and video stream
3. **Controller Test**: Test all button mappings
4. **Battery Test**: Monitor voltage under load
5. **Range Test**: Test maximum WiFi/Bluetooth range

## Troubleshooting Hardware Issues

### Common Problems

**Camera Not Detected**:
- Check camera cable connection
- Verify camera interface enabled in raspi-config
- Test with `libcamera-hello`

**Controller Not Pairing**:
- Reset controller (small button on back)
- Clear Bluetooth cache: `sudo systemctl restart bluetooth`
- Check controller battery level

**Motor Not Responding**:
- Verify power connections
- Check motor driver wiring
- Test with multimeter for continuity
- Ensure adequate power supply

**Poor WiFi Performance**:
- Check antenna connection
- Move closer to router for testing
- Consider external WiFi adapter
- Check for interference sources

### Performance Optimization

**Reduce Latency**:
- Use 5GHz WiFi when possible
- Minimize video stream resolution if needed
- Optimize control loop timing
- Use wired Ethernet for setup/testing

**Extend Battery Life**:
- Reduce camera resolution/framerate
- Lower motor speeds when possible
- Implement sleep modes for idle periods
- Use efficient power management

**Improve Reliability**:
- Use quality connectors and cables
- Implement proper strain relief
- Add redundant power connections
- Use appropriate wire gauges for current loads

## Safety Considerations

### Electrical Safety
- Always disconnect power when making connections
- Use appropriate fuses and circuit protection
- Ensure proper polarity on all connections
- Keep spare fuses and basic tools available

### Mechanical Safety
- Secure all moving parts properly
- Avoid pinch points in design
- Test emergency stop functionality
- Ensure stable center of gravity

### Operational Safety
- Test in safe, open areas initially
- Maintain visual contact during operation
- Have manual override capability
- Monitor battery levels continuously

## Maintenance Schedule

### Daily (if in regular use)
- Check battery voltage
- Verify all connections secure
- Clean camera lens if needed

### Weekly
- Inspect for loose screws or components
- Check tire wear and inflation
- Test emergency stop functions

### Monthly
- Deep clean all components
- Check servo calibration
- Update software if needed
- Backup configuration files

### As Needed
- Replace worn components
- Upgrade firmware
- Recalibrate sensors
- Replace consumables (batteries, etc.)