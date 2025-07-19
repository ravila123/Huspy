"""
Abstract base class for rover hardware interface

Defines the standard interface that all rover implementations must follow,
enabling hardware abstraction and testing with mock implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class RoverCapabilities(Enum):
    """Enumeration of rover hardware capabilities"""
    MOVEMENT = "movement"
    STEERING = "steering"
    CAMERA_PAN_TILT = "camera_pan_tilt"
    BATTERY_MONITORING = "battery_monitoring"
    CAMERA_CAPTURE = "camera_capture"
    CAMERA_STREAMING = "camera_streaming"


@dataclass
class RoverStatus:
    """Current status of the rover hardware"""
    speed: int = 0
    direction: int = 1  # 1 forward, -1 reverse, 0 stopped
    steering_angle: int = 0
    camera_pan: int = 0
    camera_tilt: int = 0
    battery_voltage: Optional[float] = None
    is_connected: bool = False
    error_message: Optional[str] = None


class RoverInterface(ABC):
    """Abstract base class for rover hardware implementations"""
    
    def __init__(self):
        self._status = RoverStatus()
        self._capabilities = set()
    
    @property
    def status(self) -> RoverStatus:
        """Get current rover status"""
        return self._status
    
    @property
    def capabilities(self) -> set[RoverCapabilities]:
        """Get supported hardware capabilities"""
        return self._capabilities.copy()
    
    def has_capability(self, capability: RoverCapabilities) -> bool:
        """Check if rover supports a specific capability"""
        return capability in self._capabilities
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the rover hardware
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Safely shutdown the rover hardware"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if rover hardware is connected and responsive
        
        Returns:
            bool: True if connected, False otherwise
        """
        pass
    
    # Movement control methods
    @abstractmethod
    def move_forward(self, speed: int) -> bool:
        """Move rover forward at specified speed
        
        Args:
            speed: Speed percentage (0-100)
            
        Returns:
            bool: True if command successful, False otherwise
        """
        pass
    
    @abstractmethod
    def move_backward(self, speed: int) -> bool:
        """Move rover backward at specified speed
        
        Args:
            speed: Speed percentage (0-100)
            
        Returns:
            bool: True if command successful, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """Stop all rover movement
        
        Returns:
            bool: True if command successful, False otherwise
        """
        pass
    
    @abstractmethod
    def set_steering_angle(self, angle: int) -> bool:
        """Set steering angle
        
        Args:
            angle: Steering angle in degrees (-35 to +35 typically)
            
        Returns:
            bool: True if command successful, False otherwise
        """
        pass
    
    # Camera control methods
    @abstractmethod
    def set_camera_pan(self, angle: int) -> bool:
        """Set camera pan angle
        
        Args:
            angle: Pan angle in degrees (-35 to +35 typically)
            
        Returns:
            bool: True if command successful, False otherwise
        """
        pass
    
    @abstractmethod
    def set_camera_tilt(self, angle: int) -> bool:
        """Set camera tilt angle
        
        Args:
            angle: Tilt angle in degrees (-35 to +35 typically)
            
        Returns:
            bool: True if command successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_battery_voltage(self) -> Optional[float]:
        """Get current battery voltage
        
        Returns:
            Optional[float]: Battery voltage in volts, None if unavailable
        """
        pass
    
    @abstractmethod
    def take_photo(self, filename: str, directory: str = ".") -> bool:
        """Take a photo with the camera
        
        Args:
            filename: Name for the photo file (without extension)
            directory: Directory to save the photo
            
        Returns:
            bool: True if photo taken successfully, False otherwise
        """
        pass
    
    # Convenience methods that can be overridden for optimization
    def set_camera_position(self, pan: int, tilt: int) -> bool:
        """Set both camera pan and tilt angles
        
        Args:
            pan: Pan angle in degrees
            tilt: Tilt angle in degrees
            
        Returns:
            bool: True if both commands successful, False otherwise
        """
        pan_success = self.set_camera_pan(pan)
        tilt_success = self.set_camera_tilt(tilt)
        return pan_success and tilt_success
    
    def center_camera(self) -> bool:
        """Center the camera (pan=0, tilt=0)
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.set_camera_position(0, 0)
    
    def center_steering(self) -> bool:
        """Center the steering (angle=0)
        
        Returns:
            bool: True if successful, False otherwise
        """
        return self.set_steering_angle(0)
    
    def emergency_stop(self) -> bool:
        """Emergency stop - stop movement and center controls
        
        Returns:
            bool: True if successful, False otherwise
        """
        stop_success = self.stop()
        steer_success = self.center_steering()
        return stop_success and steer_success
    
    def get_status_summary(self) -> str:
        """Get a human-readable status summary
        
        Returns:
            str: Status summary string
        """
        status = self.status
        if not status.is_connected:
            return "Rover: Disconnected"
        
        direction_str = "Forward" if status.direction == 1 else "Reverse" if status.direction == -1 else "Stopped"
        battery_str = f"{status.battery_voltage:.1f}V" if status.battery_voltage else "Unknown"
        
        return (f"Rover: {direction_str} {status.speed}% | "
                f"Steer: {status.steering_angle}° | "
                f"Camera: {status.camera_pan}°/{status.camera_tilt}° | "
                f"Battery: {battery_str}")