#!/usr/bin/env python3
"""
Blue Rover Web Interface

Provides a web-based interface for controlling the Blue Rover with:
- Live camera stream viewing
- Basic rover control interface
- System status dashboard
- Log file viewer and download functionality

The web interface runs on port 8000 by default and integrates with the
existing camera streaming service on port 8080.
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Thread, Lock
from typing import Dict, Any, Optional, List

try:
    from flask import Flask, render_template, request, jsonify, send_file, Response
    from flask_socketio import SocketIO, emit
except ImportError as e:
    logging.error(f"Failed to import required Flask modules: {e}")
    sys.exit(1)

# Hardware imports with graceful fallback
try:
    from picarx import Picarx
    PICARX_AVAILABLE = True
except ImportError:
    PICARX_AVAILABLE = False
    logging.warning("PicarX hardware not available - using mock implementation")

try:
    from vilib import Vilib
    VILIB_AVAILABLE = True
except ImportError:
    VILIB_AVAILABLE = False
    logging.warning("Vilib camera library not available - camera features disabled")

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.rover_config import get_config
from src.hardware.hardware_factory import create_auto_rover


class RoverWebInterface:
    """Web interface for Blue Rover control and monitoring"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.config = get_config()
        self.rover = None
        self.app = Flask(__name__, template_folder='../templates')
        self.app.config['SECRET_KEY'] = 'blue-rover-secret-key'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        self.running = False
        self.status_lock = Lock()
        self.system_status = {
            'battery_voltage': 0.0,
            'camera_active': False,
            'rover_connected': False,
            'last_update': datetime.now().isoformat()
        }
        
        self._setup_logging()
        self._setup_signal_handlers()
        self._setup_routes()
        self._setup_socketio_events()
    
    def _setup_logging(self) -> None:
        """Initialize logging system"""
        logging.basicConfig(
            level=self.config.get_log_level(),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('web_interface')
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _setup_routes(self) -> None:
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Main dashboard page"""
            return render_template('index.html', config=self.config)
        
        @self.app.route('/api/status')
        def get_status():
            """Get current system status"""
            with self.status_lock:
                return jsonify(self.system_status)
        
        @self.app.route('/api/control', methods=['POST'])
        def control_rover():
            """Handle rover control commands"""
            try:
                data = request.get_json()
                command = data.get('command')
                value = data.get('value', 0)
                
                if not self.rover:
                    return jsonify({'error': 'Rover not connected'}), 400
                
                result = self._execute_command(command, value)
                return jsonify(result)
                
            except Exception as e:
                self.logger.error(f"Control command error: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/logs')
        def list_logs():
            """List available log files"""
            try:
                log_dir = Path('logs')
                if not log_dir.exists():
                    return jsonify({'logs': []})
                
                logs = []
                for log_file in log_dir.glob('*.log'):
                    stat = log_file.stat()
                    logs.append({
                        'name': log_file.name,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                
                logs.sort(key=lambda x: x['modified'], reverse=True)
                return jsonify({'logs': logs})
                
            except Exception as e:
                self.logger.error(f"Error listing logs: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/logs/<filename>')
        def get_log_content(filename):
            """Get log file content"""
            try:
                log_file = Path('logs') / filename
                if not log_file.exists() or not log_file.is_file():
                    return jsonify({'error': 'Log file not found'}), 404
                
                # Read last 1000 lines for web display
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    content = ''.join(lines[-1000:]) if len(lines) > 1000 else ''.join(lines)
                
                return jsonify({'content': content, 'filename': filename})
                
            except Exception as e:
                self.logger.error(f"Error reading log file: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/logs/<filename>/download')
        def download_log(filename):
            """Download log file"""
            try:
                log_file = Path('logs') / filename
                if not log_file.exists() or not log_file.is_file():
                    return jsonify({'error': 'Log file not found'}), 404
                
                return send_file(log_file, as_attachment=True)
                
            except Exception as e:
                self.logger.error(f"Error downloading log file: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/snapshot', methods=['POST'])
        def take_snapshot():
            """Take a camera snapshot"""
            try:
                if not VILIB_AVAILABLE:
                    return jsonify({'error': 'Camera not available - Vilib not installed'}), 400
                
                timestamp = int(time.time())
                filename = f"web-snapshot-{timestamp}"
                log_dir = Path('logs')
                log_dir.mkdir(exist_ok=True)
                
                Vilib.take_photo(filename, str(log_dir) + "/")
                
                return jsonify({
                    'success': True,
                    'filename': f"{filename}.jpg",
                    'timestamp': timestamp
                })
                
            except Exception as e:
                self.logger.error(f"Snapshot error: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _setup_socketio_events(self) -> None:
        """Setup SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            self.logger.info(f"Client connected: {request.sid}")
            emit('status_update', self.system_status)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            self.logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('rover_command')
        def handle_rover_command(data):
            """Handle real-time rover commands via WebSocket"""
            try:
                command = data.get('command')
                value = data.get('value', 0)
                
                if self.rover:
                    result = self._execute_command(command, value)
                    emit('command_result', result)
                else:
                    emit('command_result', {'error': 'Rover not connected'})
                    
            except Exception as e:
                self.logger.error(f"WebSocket command error: {e}")
                emit('command_result', {'error': str(e)})
    
    def _execute_command(self, command: str, value: float) -> Dict[str, Any]:
        """Execute rover control command"""
        try:
            if command == 'move_forward':
                success = self.rover.move_forward(int(value))
                if success:
                    return {'success': True, 'action': f'Moving forward at speed {value}'}
                else:
                    return {'error': 'Failed to execute forward movement'}
            
            elif command == 'move_backward':
                success = self.rover.move_backward(int(value))
                if success:
                    return {'success': True, 'action': f'Moving backward at speed {value}'}
                else:
                    return {'error': 'Failed to execute backward movement'}
            
            elif command == 'stop':
                success = self.rover.stop()
                if success:
                    return {'success': True, 'action': 'Stopped'}
                else:
                    return {'error': 'Failed to stop rover'}
            
            elif command == 'steer':
                success = self.rover.set_steering_angle(int(value))
                if success:
                    return {'success': True, 'action': f'Steering set to {value}°'}
                else:
                    return {'error': f'Failed to set steering to {value}°'}
            
            elif command == 'camera_pan':
                success = self.rover.set_camera_pan(int(value))
                if success:
                    return {'success': True, 'action': f'Camera pan set to {value}°'}
                else:
                    return {'error': f'Failed to set camera pan to {value}°'}
            
            elif command == 'camera_tilt':
                success = self.rover.set_camera_tilt(int(value))
                if success:
                    return {'success': True, 'action': f'Camera tilt set to {value}°'}
                else:
                    return {'error': f'Failed to set camera tilt to {value}°'}
            
            else:
                return {'error': f'Unknown command: {command}'}
                
        except Exception as e:
            self.logger.error(f"Command execution error: {e}")
            return {'error': str(e)}
    
    def _update_system_status(self) -> None:
        """Update system status in background thread"""
        while self.running:
            try:
                with self.status_lock:
                    # Update battery voltage
                    if self.rover:
                        try:
                            voltage = self.rover.get_battery_voltage()
                            if voltage is not None:
                                self.system_status['battery_voltage'] = float(voltage)
                                self.system_status['rover_connected'] = True
                            else:
                                self.system_status['rover_connected'] = False
                        except:
                            self.system_status['rover_connected'] = False
                    
                    # Check camera status
                    self.system_status['camera_active'] = True  # Assume active if web interface is running
                    self.system_status['last_update'] = datetime.now().isoformat()
                
                # Emit status update to connected clients
                self.socketio.emit('status_update', self.system_status)
                
            except Exception as e:
                self.logger.error(f"Status update error: {e}")
            
            time.sleep(5)  # Update every 5 seconds
    
    def initialize_hardware(self) -> bool:
        """Initialize hardware components"""
        try:
            # Initialize rover hardware
            self.rover = create_auto_rover()
            if self.rover:
                self.logger.info("Rover hardware initialized successfully")
            else:
                self.logger.warning("Rover hardware initialization failed, using mock")
            
            # Initialize camera if available
            if VILIB_AVAILABLE:
                try:
                    Vilib.camera_start(vflip=False, hflip=False)
                    Vilib.display(local=True, web=True)
                    time.sleep(2)  # Camera warmup
                    self.logger.info("Camera system initialized successfully")
                except Exception as e:
                    self.logger.warning(f"Camera initialization failed: {e}")
            else:
                self.logger.info("Camera system not available - Vilib not installed")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Hardware initialization failed: {e}")
            return False
    
    def shutdown_hardware(self) -> None:
        """Safely shutdown hardware components"""
        try:
            if self.rover:
                self.rover.stop()
                self.logger.info("Rover hardware shutdown complete")
        except Exception as e:
            self.logger.warning(f"Error during rover shutdown: {e}")
        
        if VILIB_AVAILABLE:
            try:
                Vilib.camera_close()
                self.logger.info("Camera shutdown complete")
            except Exception as e:
                self.logger.warning(f"Error during camera shutdown: {e}")
        else:
            self.logger.info("Camera shutdown skipped - Vilib not available")
    
    def run(self) -> None:
        """Start the web interface server"""
        if not self.initialize_hardware():
            self.logger.error("Failed to initialize hardware")
            # Continue anyway for web interface functionality
        
        self.running = True
        
        # Start status update thread
        status_thread = Thread(target=self._update_system_status, daemon=True)
        status_thread.start()
        
        self.logger.info(f"Starting web interface on port {self.port}")
        
        try:
            # Run the Flask-SocketIO server
            self.socketio.run(
                self.app,
                host='0.0.0.0',
                port=self.port,
                debug=self.config.debug_mode,
                allow_unsafe_werkzeug=True
            )
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Web server error: {e}")
        finally:
            self.running = False
            self.shutdown_hardware()
            self.logger.info("Web interface stopped")


def main():
    """Entry point for web interface"""
    import argparse
    parser = argparse.ArgumentParser(description='Blue Rover Web Interface')
    parser.add_argument('--port', type=int, default=8000,
                       help='Web interface port (default: 8000)')
    parser.add_argument('--config', type=str,
                       help='Configuration file path')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Set up configuration
    if args.config:
        from config.rover_config import RoverConfig, set_config
        config = RoverConfig.from_file(args.config)
        set_config(config)
    
    if args.debug:
        config = get_config()
        config.debug_mode = True
        config.logging.level = "DEBUG"
    
    try:
        web_interface = RoverWebInterface(port=args.port)
        web_interface.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()