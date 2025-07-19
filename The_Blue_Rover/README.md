# Blue Rover - Raspberry Pi Robot Control System

A comprehensive robotics control system for Raspberry Pi featuring PS5 controller integration, manual keyboard control, live camera streaming, and battery monitoring. Designed for easy deployment and remote operation via SSH.

## Features

- **Multiple Control Modes**: PS5 controller, keyboard control, and web interface
- **Live Camera Streaming**: Real-time video feed with pan/tilt control
- **Battery Monitoring**: Continuous voltage monitoring with alerts
- **Remote SSH Access**: Secure remote operation from anywhere
- **Automated Setup**: One-command deployment on Raspberry Pi
- **Service Management**: Systemd integration for reliable operation
- **Web Interface**: Browser-based control and monitoring dashboard
- **Hardware Abstraction**: Modular design supporting different rover platforms

## Quick Start

### Prerequisites

- Raspberry Pi (3B+, 4, or Zero 2W) with Raspberry Pi OS
- PicarX robot kit or compatible hardware
- PS5 DualSense controller (optional)
- Camera module (optional)
- SSH access to your Pi

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ravila123/blue-rover.git
   cd blue-rover
   ```

2. **Run the setup script**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Start the rover**:
   ```bash
   # For PS5 controller mode
   ./run_rover.sh ps5
   
   # For keyboard control
   ./run_rover.sh manual
   
   # For web interface
   ./run_rover.sh web
   
   # For battery monitoring only
   ./run_rover.sh monitor
   ```

### Remote Access Setup

1. **Configure SSH keys** (if not already done):
   ```bash
   # On your local machine
   ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
   ssh-copy-id pi@your-pi-ip-address
   ```

2. **Connect remotely**:
   ```bash
   ssh pi@your-pi-ip-address
   cd blue-rover
   ./run_rover.sh web  # Access via browser at http://your-pi-ip:8080
   ```

## Project Structure

```
blue-rover/
├── README.md                 # This file
├── setup.sh                 # Main setup script
├── run_rover.sh             # Launcher script
├── requirements.txt          # Python dependencies
├── src/                     # Source code
│   ├── blue_rover.py        # Main rover control
│   ├── ps5_control.py       # PS5 controller interface
│   ├── battery_monitor.py   # Battery monitoring
│   └── utils/               # Utility modules
├── config/                  # Configuration files
│   ├── systemd/            # Service definitions
│   └── ssh/                # SSH templates
├── scripts/                 # Setup and utility scripts
├── tests/                   # Test suite
├── docs/                    # Additional documentation
└── logs/                    # Runtime logs
```

## Usage

### Control Modes

**PS5 Controller Mode**:
- Left stick: Forward/backward movement
- Right stick: Steering
- L2/R2: Camera pan control
- L1/R1: Camera tilt control
- Triangle: Emergency stop

**Keyboard Control**:
- WASD: Movement control
- Arrow keys: Camera control
- Space: Emergency stop
- Q: Quit

**Web Interface**:
- Access at `http://your-pi-ip:8080`
- Virtual joystick for movement
- Camera controls and live stream
- System status dashboard

### Service Management

The system uses systemd services for background operations:

```bash
# Check service status
systemctl --user status blue-rover-battery
systemctl --user status blue-rover-camera

# Start/stop services
systemctl --user start blue-rover-battery
systemctl --user stop blue-rover-battery

# View logs
journalctl --user -u blue-rover-battery -f
```

## Configuration

Configuration files are located in the `config/` directory:

- `rover_config.json`: Main application settings
- `systemd/`: Service definitions
- `ssh/`: SSH configuration templates

Example configuration:
```json
{
  "camera_enabled": true,
  "camera_port": 8080,
  "log_level": "INFO",
  "battery_check_interval": 5,
  "max_speed": 100,
  "steering_range": 35
}
```

## Hardware Requirements

See [HARDWARE.md](docs/HARDWARE.md) for detailed hardware requirements and setup instructions.

## Troubleshooting

Common issues and solutions are documented in [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Development

For development guidelines and contribution information, see [DEVELOPMENT.md](docs/DEVELOPMENT.md).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- Create an issue on GitHub for bug reports
- Check the troubleshooting guide for common problems
- Review the hardware documentation for setup issues

## Acknowledgments

- Built for PicarX robot platform
- Inspired by the Raspberry Pi robotics community
- Thanks to all contributors and testers