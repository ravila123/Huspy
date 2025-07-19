"""
Hardware factory for creating rover instances

Provides a factory pattern for creating different types of rover hardware
implementations, with automatic detection and fallback capabilities.
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any

from .rover_interface import RoverInterface
from .picarx_rover import PicarXRover
from .mock_rover import MockRover


class RoverType(Enum):
    """Enumeration of supported rover types"""
    PICARX = "picarx"
    MOCK = "mock"
    AUTO = "auto"  # Automatic detection


class HardwareFactory:
    """Factory class for creating rover hardware instances"""
    
    @staticmethod
    def create_rover(rover_type: RoverType = RoverType.AUTO, 
                    **kwargs) -> RoverInterface:
        """Create a rover instance of the specified type
        
        Args:
            rover_type: Type of rover to create
            **kwargs: Additional arguments passed to rover constructor
            
        Returns:
            RoverInterface: Configured rover instance
            
        Raises:
            ValueError: If rover type is not supported
            RuntimeError: If rover creation fails
        """
        try:
            if rover_type == RoverType.AUTO:
                return HardwareFactory._create_auto_detected_rover(**kwargs)
            elif rover_type == RoverType.PICARX:
                return HardwareFactory._create_picarx_rover(**kwargs)
            elif rover_type == RoverType.MOCK:
                return HardwareFactory._create_mock_rover(**kwargs)
            else:
                raise ValueError(f"Unsupported rover type: {rover_type}")
                
        except Exception as e:
            error_msg = f"Failed to create rover of type {rover_type}: {e}"
            logging.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    @staticmethod
    def _create_auto_detected_rover(**kwargs) -> RoverInterface:
        """Create rover with automatic hardware detection"""
        logging.info("Attempting automatic rover hardware detection")
        
        # Try PicarX first
        try:
            rover = HardwareFactory._create_picarx_rover(**kwargs)
            if rover.initialize():
                logging.info("Auto-detected PicarX hardware")
                return rover
            else:
                rover.shutdown()
                logging.warning("PicarX hardware detected but initialization failed")
        except Exception as e:
            logging.debug(f"PicarX detection failed: {e}")
        
        # Fall back to mock rover
        logging.info("Falling back to mock rover implementation")
        return HardwareFactory._create_mock_rover(**kwargs)
    
    @staticmethod
    def _create_picarx_rover(**kwargs) -> PicarXRover:
        """Create PicarX rover instance"""
        logging.debug("Creating PicarX rover instance")
        
        # Extract PicarX-specific parameters
        camera_enabled = kwargs.get('camera_enabled', True)
        camera_warmup_time = kwargs.get('camera_warmup_time', 2.0)
        
        return PicarXRover(
            camera_enabled=camera_enabled,
            camera_warmup_time=camera_warmup_time
        )
    
    @staticmethod
    def _create_mock_rover(**kwargs) -> MockRover:
        """Create mock rover instance"""
        logging.debug("Creating mock rover instance")
        
        # Extract mock-specific parameters
        simulate_battery_drain = kwargs.get('simulate_battery_drain', True)
        initial_battery_voltage = kwargs.get('initial_battery_voltage', 8.0)
        connection_reliability = kwargs.get('connection_reliability', 0.95)
        
        return MockRover(
            simulate_battery_drain=simulate_battery_drain,
            initial_battery_voltage=initial_battery_voltage,
            connection_reliability=connection_reliability
        )
    
    @staticmethod
    def get_available_rover_types() -> list[RoverType]:
        """Get list of available rover types
        
        Returns:
            list[RoverType]: List of rover types that can be created
        """
        available_types = [RoverType.MOCK, RoverType.AUTO]
        
        # Check if PicarX hardware is available
        try:
            from picarx import Picarx
            available_types.append(RoverType.PICARX)
        except ImportError:
            logging.debug("PicarX hardware not available")
        
        return available_types
    
    @staticmethod
    def detect_hardware() -> Dict[str, Any]:
        """Detect available hardware and return information
        
        Returns:
            Dict[str, Any]: Hardware detection results
        """
        detection_results = {
            'picarx_available': False,
            'camera_available': False,
            'recommended_type': RoverType.MOCK,
            'detection_errors': []
        }
        
        # Test PicarX availability
        try:
            from picarx import Picarx
            detection_results['picarx_available'] = True
            detection_results['recommended_type'] = RoverType.PICARX
            logging.info("PicarX hardware modules detected")
        except ImportError as e:
            detection_results['detection_errors'].append(f"PicarX not available: {e}")
            logging.debug(f"PicarX detection failed: {e}")
        
        # Test camera availability
        try:
            from vilib import Vilib
            detection_results['camera_available'] = True
            logging.info("Camera modules detected")
        except ImportError as e:
            detection_results['detection_errors'].append(f"Camera not available: {e}")
            logging.debug(f"Camera detection failed: {e}")
        
        return detection_results
    
    @staticmethod
    def create_rover_from_config(config: Dict[str, Any]) -> RoverInterface:
        """Create rover from configuration dictionary
        
        Args:
            config: Configuration dictionary with rover settings
            
        Returns:
            RoverInterface: Configured rover instance
        """
        rover_type_str = config.get('rover_type', 'auto').lower()
        
        # Convert string to enum
        rover_type_map = {
            'picarx': RoverType.PICARX,
            'mock': RoverType.MOCK,
            'auto': RoverType.AUTO
        }
        
        rover_type = rover_type_map.get(rover_type_str, RoverType.AUTO)
        
        # Extract rover-specific configuration
        rover_config = config.get('rover_config', {})
        
        logging.info(f"Creating rover from config: type={rover_type}, config={rover_config}")
        return HardwareFactory.create_rover(rover_type, **rover_config)


# Convenience functions for common use cases
def create_picarx_rover(camera_enabled: bool = True) -> PicarXRover:
    """Convenience function to create PicarX rover
    
    Args:
        camera_enabled: Whether to enable camera functionality
        
    Returns:
        PicarXRover: PicarX rover instance
    """
    return HardwareFactory.create_rover(
        RoverType.PICARX, 
        camera_enabled=camera_enabled
    )


def create_mock_rover(connection_reliability: float = 0.95) -> MockRover:
    """Convenience function to create mock rover
    
    Args:
        connection_reliability: Simulated connection reliability (0.0-1.0)
        
    Returns:
        MockRover: Mock rover instance
    """
    return HardwareFactory.create_rover(
        RoverType.MOCK,
        connection_reliability=connection_reliability
    )


def create_auto_rover(**kwargs) -> RoverInterface:
    """Convenience function to create rover with automatic detection
    
    Args:
        **kwargs: Additional configuration arguments
        
    Returns:
        RoverInterface: Auto-detected rover instance
    """
    return HardwareFactory.create_rover(RoverType.AUTO, **kwargs)