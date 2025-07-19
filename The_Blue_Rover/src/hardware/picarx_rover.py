"""
PicarX rover implementation

Concrete implementation of RoverInterface for PicarX hardware,
wrapping existing PicarX functionality with the standard interface.
"""

import logging
from pathlib import Path
from time import sleep
from typing import Optional

try:
    from picarx import Picarx
    from vilib import Vilib
    HARDWARE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"PicarX hardware modules not available: {e}")
    HARDWARE_AVAILABLE = False
    # Create dummy classes for development
    class Picarx:
        def __init__(self): pass
        def forward(self, speed): pass
        def backward(self, speed): pass
        def stop(self): pass
        def set_dir_servo_angle(self, angle): pass
        def set_cam_pan_angle(self, angle): pass
        def set_cam_tilt_angle(self, angle): pass
        def get_battery_voltage(self): return 7.4
    
    class Vilib:
        @staticmethod
        def camera_start(**kwargs): pass
        @staticmethod
        def camera_close(): pass
        @staticmethod
        def display(**kwargs): pass
        @staticmethod
        def take_photo(name, path): pass

from .rover_interface import RoverInterface, RoverCapabilities, RoverStatus


class PicarXRover(RoverInterface):
    """PicarX hardware implementation of RoverInterface"""
    
    def __init__(self, camera_enabled: bool = True, camera_warmup_time: float = 2.0):
        super().__init__()
        self.px: Optional[Picarx] = None
        self.camera_enabled = camera_enabled
        self.camera_warmup_time = camera_warmup_time
        self.camera_initialized = False
        
        # Set supported capabilities
        self._capabilities = {
            RoverCapabilities.MOVEMENT,
            RoverCapabilities.STEERING,
            RoverCapabilities.CAMERA_PAN_TILT,
            RoverCapabilities.BATTERY_MONITORING,
            RoverCapabilities.CAMERA_CAPTURE,
            RoverCapabilities.CAMERA_STREAMING
        }
    
    def initialize(self) -> bool:
        """Initialize PicarX hardware"""
        try:
            if not HARDWARE_AVAILABLE:
                logging.warning("PicarX hardware not available, using mock implementation")
                self._status.is_connected = False
                self._status.error_message = "Hardware modules not available"
                return False
            
            # Initialize PicarX
            self.px = Picarx()
            logging.info("PicarX hardware initialized successfully")
            
            # Initialize camera if enabled
            if self.camera_enabled:
                if not self._initialize_camera():
                    logging.warning("Camera initialization failed, continuing without camera")
                    self._capabilities.discard(RoverCapabilities.CAMERA_CAPTURE)
                    self._capabilities.discard(RoverCapabilities.CAMERA_STREAMING)
            
            # Update status
            self._status.is_connected = True
            self._status.error_message = None
            
            # Center all controls
            self._center_all_controls()
            
            return True
            
        except Exception as e:
            error_msg = f"PicarX initialization failed: {e}"
            logging.error(error_msg)
            self._status.is_connected = False
            self._status.error_message = error_msg
            return False
    
    def _initialize_camera(self) -> bool:
        """Initialize camera system"""
        try:
            Vilib.camera_start(vflip=False, hflip=False)
            Vilib.display(local=True, web=True)
            sleep(self.camera_warmup_time)
            self.camera_initialized = True
            logging.info("Camera system initialized successfully")
            return True
        except Exception as e:
            logging.error(f"Camera initialization failed: {e}")
            return False
    
    def _center_all_controls(self) -> None:
        """Center steering and camera on initialization"""
        try:
            if self.px:
                self.px.set_dir_servo_angle(0)
                self.px.set_cam_pan_angle(0)
                self.px.set_cam_tilt_angle(0)
                self._status.steering_angle = 0
                self._status.camera_pan = 0
                self._status.camera_tilt = 0
        except Exception as e:
            logging.warning(f"Failed to center controls: {e}")
    
    def shutdown(self) -> None:
        """Safely shutdown PicarX hardware"""
        try:
            if self.px:
                # Stop movement and center controls
                self.px.stop()
                self.px.set_dir_servo_angle(0)
                self.px.set_cam_pan_angle(0)
                self.px.set_cam_tilt_angle(0)
                logging.info("PicarX hardware shutdown complete")
        except Exception as e:
            logging.warning(f"Error during PicarX shutdown: {e}")
        
        try:
            if self.camera_initialized:
                Vilib.camera_close()
                self.camera_initialized = False
                logging.info("Camera system shutdown complete")
        except Exception as e:
            logging.warning(f"Error during camera shutdown: {e}")
        
        self._status.is_connected = False
        self._status.speed = 0
        self._status.direction = 0
    
    def is_connected(self) -> bool:
        """Check if PicarX hardware is connected"""
        return self._status.is_connected and self.px is not None
    
    def move_forward(self, speed: int) -> bool:
        """Move rover forward at specified speed"""
        if not self.is_connected():
            return False
        
        try:
            # Clamp speed to valid range
            speed = max(0, min(100, speed))
            
            if speed == 0:
                return self.stop()
            
            self.px.forward(speed)
            self._status.speed = speed
            self._status.direction = 1
            return True
            
        except Exception as e:
            logging.error(f"Failed to move forward: {e}")
            self._status.error_message = str(e)
            return False
    
    def move_backward(self, speed: int) -> bool:
        """Move rover backward at specified speed"""
        if not self.is_connected():
            return False
        
        try:
            # Clamp speed to valid range
            speed = max(0, min(100, speed))
            
            if speed == 0:
                return self.stop()
            
            self.px.backward(speed)
            self._status.speed = speed
            self._status.direction = -1
            return True
            
        except Exception as e:
            logging.error(f"Failed to move backward: {e}")
            self._status.error_message = str(e)
            return False
    
    def stop(self) -> bool:
        """Stop all rover movement"""
        if not self.is_connected():
            return False
        
        try:
            self.px.stop()
            self._status.speed = 0
            self._status.direction = 0
            return True
            
        except Exception as e:
            logging.error(f"Failed to stop: {e}")
            self._status.error_message = str(e)
            return False
    
    def set_steering_angle(self, angle: int) -> bool:
        """Set steering angle"""
        if not self.is_connected():
            return False
        
        try:
            # Clamp angle to typical range
            angle = max(-35, min(35, angle))
            
            self.px.set_dir_servo_angle(angle)
            self._status.steering_angle = angle
            return True
            
        except Exception as e:
            logging.error(f"Failed to set steering angle: {e}")
            self._status.error_message = str(e)
            return False
    
    def set_camera_pan(self, angle: int) -> bool:
        """Set camera pan angle"""
        if not self.is_connected():
            return False
        
        try:
            # Clamp angle to typical range
            angle = max(-35, min(35, angle))
            
            self.px.set_cam_pan_angle(angle)
            self._status.camera_pan = angle
            return True
            
        except Exception as e:
            logging.error(f"Failed to set camera pan: {e}")
            self._status.error_message = str(e)
            return False
    
    def set_camera_tilt(self, angle: int) -> bool:
        """Set camera tilt angle"""
        if not self.is_connected():
            return False
        
        try:
            # Clamp angle to typical range
            angle = max(-35, min(35, angle))
            
            self.px.set_cam_tilt_angle(angle)
            self._status.camera_tilt = angle
            return True
            
        except Exception as e:
            logging.error(f"Failed to set camera tilt: {e}")
            self._status.error_message = str(e)
            return False
    
    def get_battery_voltage(self) -> Optional[float]:
        """Get current battery voltage"""
        if not self.is_connected():
            return None
        
        try:
            voltage = self.px.get_battery_voltage()
            if voltage is not None:
                self._status.battery_voltage = float(voltage)
                return self._status.battery_voltage
            return None
            
        except AttributeError:
            logging.warning("Battery voltage method not available on this hardware")
            return None
        except Exception as e:
            logging.error(f"Failed to read battery voltage: {e}")
            self._status.error_message = str(e)
            return None
    
    def take_photo(self, filename: str, directory: str = ".") -> bool:
        """Take a photo with the camera"""
        if not self.is_connected() or not self.camera_initialized:
            return False
        
        if not self.has_capability(RoverCapabilities.CAMERA_CAPTURE):
            logging.warning("Camera capture not available")
            return False
        
        try:
            # Ensure directory exists
            dir_path = Path(directory)
            dir_path.mkdir(parents=True, exist_ok=True)
            
            # Take photo using Vilib
            Vilib.take_photo(filename, str(dir_path) + "/")
            
            # Verify file was created
            photo_path = dir_path / f"{filename}.jpg"
            if photo_path.exists():
                logging.info(f"Photo saved: {photo_path}")
                return True
            else:
                logging.error(f"Photo file not created: {photo_path}")
                return False
                
        except Exception as e:
            logging.error(f"Failed to take photo: {e}")
            self._status.error_message = str(e)
            return False
    
    def set_camera_position(self, pan: int, tilt: int) -> bool:
        """Set both camera pan and tilt angles (optimized for PicarX)"""
        if not self.is_connected():
            return False
        
        try:
            # Clamp angles to typical range
            pan = max(-35, min(35, pan))
            tilt = max(-35, min(35, tilt))
            
            # Set both angles
            self.px.set_cam_pan_angle(pan)
            self.px.set_cam_tilt_angle(tilt)
            
            # Update status
            self._status.camera_pan = pan
            self._status.camera_tilt = tilt
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to set camera position: {e}")
            self._status.error_message = str(e)
            return False