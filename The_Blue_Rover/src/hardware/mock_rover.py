"""
Mock rover implementation for testing and development

Provides a software-only implementation of RoverInterface that simulates
rover behavior without requiring actual hardware. Useful for development,
testing, and CI/CD environments.
"""

import logging
import random
from pathlib import Path
from time import time
from typing import Optional

from .rover_interface import RoverInterface, RoverCapabilities, RoverStatus


class MockRover(RoverInterface):
    """Mock implementation of RoverInterface for testing and development"""
    
    def __init__(self, 
                 simulate_battery_drain: bool = True,
                 initial_battery_voltage: float = 8.0,
                 connection_reliability: float = 0.95):
        """Initialize mock rover
        
        Args:
            simulate_battery_drain: Whether to simulate battery voltage decreasing over time
            initial_battery_voltage: Starting battery voltage
            connection_reliability: Probability of successful operations (0.0-1.0)
        """
        super().__init__()
        self.simulate_battery_drain = simulate_battery_drain
        self.initial_battery_voltage = initial_battery_voltage
        self.connection_reliability = connection_reliability
        self.start_time = time()
        self.initialized = False
        
        # Set all capabilities as supported
        self._capabilities = {
            RoverCapabilities.MOVEMENT,
            RoverCapabilities.STEERING,
            RoverCapabilities.CAMERA_PAN_TILT,
            RoverCapabilities.BATTERY_MONITORING,
            RoverCapabilities.CAMERA_CAPTURE,
            RoverCapabilities.CAMERA_STREAMING
        }
        
        # Initialize status
        self._status = RoverStatus(
            battery_voltage=initial_battery_voltage,
            is_connected=False
        )
    
    def _simulate_operation_success(self) -> bool:
        """Simulate operation success based on connection reliability"""
        return random.random() < self.connection_reliability
    
    def _update_battery_voltage(self) -> None:
        """Update simulated battery voltage"""
        if not self.simulate_battery_drain:
            return
        
        # Simulate battery drain over time (very slow for testing)
        elapsed_hours = (time() - self.start_time) / 3600
        voltage_drop = elapsed_hours * 0.1  # 0.1V per hour
        
        # Add some random variation
        voltage_variation = random.uniform(-0.05, 0.05)
        
        self._status.battery_voltage = max(
            5.0,  # Minimum voltage
            self.initial_battery_voltage - voltage_drop + voltage_variation
        )
    
    def initialize(self) -> bool:
        """Initialize mock rover"""
        try:
            logging.info("Initializing mock rover")
            
            # Simulate initialization delay
            import time
            time.sleep(0.1)
            
            # Simulate occasional initialization failure
            if not self._simulate_operation_success():
                error_msg = "Mock initialization failed (simulated)"
                logging.error(error_msg)
                self._status.error_message = error_msg
                return False
            
            self.initialized = True
            self._status.is_connected = True
            self._status.error_message = None
            
            # Reset to center position
            self._status.speed = 0
            self._status.direction = 0
            self._status.steering_angle = 0
            self._status.camera_pan = 0
            self._status.camera_tilt = 0
            
            logging.info("Mock rover initialized successfully")
            return True
            
        except Exception as e:
            error_msg = f"Mock rover initialization failed: {e}"
            logging.error(error_msg)
            self._status.error_message = error_msg
            return False
    
    def shutdown(self) -> None:
        """Shutdown mock rover"""
        logging.info("Shutting down mock rover")
        self.initialized = False
        self._status.is_connected = False
        self._status.speed = 0
        self._status.direction = 0
    
    def is_connected(self) -> bool:
        """Check if mock rover is connected"""
        return self.initialized and self._status.is_connected
    
    def move_forward(self, speed: int) -> bool:
        """Simulate forward movement"""
        if not self.is_connected():
            return False
        
        if not self._simulate_operation_success():
            self._status.error_message = "Mock forward movement failed (simulated)"
            return False
        
        # Clamp speed
        speed = max(0, min(100, speed))
        
        if speed == 0:
            return self.stop()
        
        self._status.speed = speed
        self._status.direction = 1
        self._status.error_message = None
        
        logging.debug(f"Mock rover moving forward at {speed}%")
        return True
    
    def move_backward(self, speed: int) -> bool:
        """Simulate backward movement"""
        if not self.is_connected():
            return False
        
        if not self._simulate_operation_success():
            self._status.error_message = "Mock backward movement failed (simulated)"
            return False
        
        # Clamp speed
        speed = max(0, min(100, speed))
        
        if speed == 0:
            return self.stop()
        
        self._status.speed = speed
        self._status.direction = -1
        self._status.error_message = None
        
        logging.debug(f"Mock rover moving backward at {speed}%")
        return True
    
    def stop(self) -> bool:
        """Simulate stopping"""
        if not self.is_connected():
            return False
        
        if not self._simulate_operation_success():
            self._status.error_message = "Mock stop failed (simulated)"
            return False
        
        self._status.speed = 0
        self._status.direction = 0
        self._status.error_message = None
        
        logging.debug("Mock rover stopped")
        return True
    
    def set_steering_angle(self, angle: int) -> bool:
        """Simulate steering"""
        if not self.is_connected():
            return False
        
        if not self._simulate_operation_success():
            self._status.error_message = "Mock steering failed (simulated)"
            return False
        
        # Clamp angle
        angle = max(-35, min(35, angle))
        
        self._status.steering_angle = angle
        self._status.error_message = None
        
        logging.debug(f"Mock rover steering set to {angle}°")
        return True
    
    def set_camera_pan(self, angle: int) -> bool:
        """Simulate camera pan"""
        if not self.is_connected():
            return False
        
        if not self._simulate_operation_success():
            self._status.error_message = "Mock camera pan failed (simulated)"
            return False
        
        # Clamp angle
        angle = max(-35, min(35, angle))
        
        self._status.camera_pan = angle
        self._status.error_message = None
        
        logging.debug(f"Mock camera pan set to {angle}°")
        return True
    
    def set_camera_tilt(self, angle: int) -> bool:
        """Simulate camera tilt"""
        if not self.is_connected():
            return False
        
        if not self._simulate_operation_success():
            self._status.error_message = "Mock camera tilt failed (simulated)"
            return False
        
        # Clamp angle
        angle = max(-35, min(35, angle))
        
        self._status.camera_tilt = angle
        self._status.error_message = None
        
        logging.debug(f"Mock camera tilt set to {angle}°")
        return True
    
    def get_battery_voltage(self) -> Optional[float]:
        """Get simulated battery voltage"""
        if not self.is_connected():
            return None
        
        if not self._simulate_operation_success():
            self._status.error_message = "Mock battery reading failed (simulated)"
            return None
        
        self._update_battery_voltage()
        self._status.error_message = None
        
        logging.debug(f"Mock battery voltage: {self._status.battery_voltage:.2f}V")
        return self._status.battery_voltage
    
    def take_photo(self, filename: str, directory: str = ".") -> bool:
        """Simulate taking a photo"""
        if not self.is_connected():
            return False
        
        if not self._simulate_operation_success():
            self._status.error_message = "Mock photo capture failed (simulated)"
            return False
        
        try:
            # Create directory if it doesn't exist
            dir_path = Path(directory)
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create a mock photo file
            photo_path = dir_path / f"{filename}.jpg"
            
            # Write a simple mock JPEG header to make it look like a real file
            mock_jpeg_data = (
                b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
                b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
                b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
                b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
                b'\xff\xc0\x00\x11\x08\x00\x64\x00\x64\x03\x01"\x00\x02\x11\x01\x03\x11\x01'
                b'\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08'
                b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9'
            )
            
            with open(photo_path, 'wb') as f:
                f.write(mock_jpeg_data)
            
            self._status.error_message = None
            logging.info(f"Mock photo saved: {photo_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to create mock photo: {e}"
            logging.error(error_msg)
            self._status.error_message = error_msg
            return False
    
    def set_connection_reliability(self, reliability: float) -> None:
        """Set the connection reliability for testing failure scenarios
        
        Args:
            reliability: Probability of successful operations (0.0-1.0)
        """
        self.connection_reliability = max(0.0, min(1.0, reliability))
        logging.info(f"Mock rover connection reliability set to {self.connection_reliability:.2%}")
    
    def simulate_disconnection(self) -> None:
        """Simulate a connection loss"""
        self._status.is_connected = False
        self._status.error_message = "Connection lost (simulated)"
        logging.warning("Mock rover connection lost (simulated)")
    
    def simulate_reconnection(self) -> bool:
        """Simulate reconnection"""
        if self.initialized:
            self._status.is_connected = True
            self._status.error_message = None
            logging.info("Mock rover reconnected (simulated)")
            return True
        return False