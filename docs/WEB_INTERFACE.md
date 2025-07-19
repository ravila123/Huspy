# Blue Rover Web Interface

The Blue Rover Web Interface provides a comprehensive browser-based control and monitoring system for the Blue Rover robot. This interface allows remote operation, system monitoring, and log management through any modern web browser.

## Features

### 🎮 Rover Control
- **Movement Controls**: Forward, backward, left, right steering with adjustable speed
- **Emergency Stop**: Immediate stop button for safety
- **Keyboard Controls**: WASD keys for movement, X/Space for stop, T for snapshot
- **Speed Control**: Adjustable speed slider (0-100%)

### 📹 Camera System
- **Live Stream**: Real-time camera feed display
- **Camera Controls**: Pan and tilt adjustment (-35° to +35°)
- **Snapshot Capture**: Take and save photos with timestamp
- **Stream Integration**: Seamless integration with camera streaming service

### 📊 System Monitoring
- **Real-time Status**: Connection, battery voltage, camera status
- **Battery Monitoring**: Voltage display with color-coded alerts
- **Connection Status**: Live connection monitoring with WebSocket
- **Last Update Timestamp**: Shows when status was last refreshed

### 📋 Log Management
- **Log Viewer**: Browse and view log files in real-time
- **Log Download**: Download log files for offline analysis
- **Multiple Log Types**: Support for different log file formats
- **Auto-refresh**: Automatic log list updates

## Getting Started

### Prerequisites
- Blue Rover system properly set up and configured
- Network connectivity (WiFi or Ethernet)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Starting the Web Interface

1. **Start the web interface**:
   ```bash
   ./run_rover.sh web
   ```

2. **Access the interface**:
   - Open your web browser
   - Navigate to `http://[ROVER_IP]:8000`
   - Replace `[ROVER_IP]` with your Raspberry Pi's IP address

3. **Camera stream** (if available):
   - Camera stream is accessible at `http://[ROVER_IP]:8080/stream.mjpg`
   - Integrated automatically in the web interface

### Finding Your Rover's IP Address

On the Raspberry Pi, run:
```bash
hostname -I
```

Or check your router's admin panel for connected devices.

## Interface Layout

### Status Bar
- **Connection**: Shows if the web interface is connected to the rover
- **Battery**: Current battery voltage with color coding:
  - Green: >6.5V (Good)
  - Orange: 6.0-6.5V (Low)
  - Red: <6.0V (Critical)
- **Camera**: Camera system status
- **Last Update**: Timestamp of last status update

### Camera Panel
- **Live Stream**: Real-time video feed from rover camera
- **Snapshot Button**: Capture and save photos
- **Pan Control**: Horizontal camera movement (-35° to +35°)
- **Tilt Control**: Vertical camera movement (-35° to +35°)

### Control Panel
- **Movement Buttons**: 
  - Forward/Backward: Move rover in specified direction
  - Left/Right: Steer rover (hold to maintain steering)
  - STOP: Emergency stop (red button)
- **Speed Slider**: Adjust movement speed (0-100%)

### Log Viewer
- **Log Selection**: Dropdown to choose which log file to view
- **Refresh Button**: Update the list of available log files
- **Download Button**: Download the currently selected log file
- **Log Content**: Scrollable text area showing log contents

## Controls Reference

### Mouse/Touch Controls
- **Click and Hold**: Movement and steering buttons work with click-and-hold
- **Sliders**: Drag to adjust speed, camera pan/tilt
- **Buttons**: Single click for actions like stop, snapshot

### Keyboard Shortcuts
- **W**: Move forward
- **S**: Move backward  
- **A**: Steer left
- **D**: Steer right
- **X** or **Space**: Emergency stop
- **T**: Take snapshot

*Note: Keyboard shortcuts work when not typing in input fields*

## API Endpoints

The web interface provides several REST API endpoints for integration:

### Status
- `GET /api/status` - Get current system status

### Control
- `POST /api/control` - Send control commands
  ```json
  {
    "command": "move_forward|move_backward|stop|steer|camera_pan|camera_tilt",
    "value": 0-100
  }
  ```

### Logs
- `GET /api/logs` - List available log files
- `GET /api/logs/<filename>` - Get log file content
- `GET /api/logs/<filename>/download` - Download log file

### Camera
- `POST /api/snapshot` - Take a camera snapshot

## WebSocket Events

Real-time communication uses WebSocket events:

### Client to Server
- `rover_command` - Send real-time control commands

### Server to Client
- `status_update` - Receive system status updates
- `command_result` - Receive command execution results

## Troubleshooting

### Web Interface Won't Load
1. Check that the web service is running: `./run_rover.sh web`
2. Verify the IP address and port (default: 8000)
3. Check firewall settings on the Raspberry Pi
4. Ensure network connectivity between browser and rover

### Camera Stream Not Working
1. Verify camera is connected and working
2. Check camera stream URL: `http://[ROVER_IP]:8080/stream.mjpg`
3. Restart the web interface
4. Check camera permissions and hardware

### Controls Not Responding
1. Check WebSocket connection status (top of page)
2. Verify rover hardware is connected
3. Check for error messages in browser console (F12)
4. Restart the web interface service

### Battery Status Shows Unknown
1. Check rover hardware connection
2. Verify battery monitoring is working
3. Check log files for hardware errors

## Security Considerations

### Network Security
- The web interface runs on all network interfaces (0.0.0.0)
- Consider using a VPN for remote access over the internet
- Monitor access logs for unauthorized connections

### Access Control
- No built-in authentication (suitable for local networks)
- Consider adding reverse proxy with authentication for public access
- Limit network access using firewall rules

## Configuration

### Port Configuration
Default ports can be changed in the rover configuration:
- Web interface: 8000 (configurable via `--port` argument)
- Camera stream: 8080 (configured in camera service)

### Custom Configuration
```bash
./run_rover.sh web --port 9000 --config config/rover_config_custom.json
```

## Development

### Adding Custom Features
The web interface is built with:
- **Backend**: Flask + Flask-SocketIO (Python)
- **Frontend**: HTML5 + JavaScript + WebSocket
- **Styling**: CSS3 with responsive design

### File Structure
```
templates/index.html          # Main web interface template
src/web_interface.py          # Flask web server implementation
static/                       # Static assets (if needed)
```

### Extending the Interface
1. Add new routes in `_setup_routes()` method
2. Add WebSocket events in `_setup_socketio_events()` method
3. Update HTML template for new UI elements
4. Test with `python3 test_web_interface_structure.py`

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review log files in the `logs/` directory
3. Check the main project documentation
4. Verify hardware connections and setup

The web interface provides a powerful and user-friendly way to control and monitor your Blue Rover system remotely!