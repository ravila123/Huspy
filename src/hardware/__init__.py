"""
Hardware abstraction layer for Blue Rover

This package provides hardware abstraction interfaces and implementations
for different rover types, enabling testing with mock hardware and
supporting multiple rover platforms.
"""

from .rover_interface import RoverInterface, RoverCapabilities
from .picarx_rover import PicarXRover
from .mock_rover import MockRover
from .hardware_factory import HardwareFactory, RoverType

__all__ = [
    'RoverInterface',
    'RoverCapabilities', 
    'PicarXRover',
    'MockRover',
    'HardwareFactory',
    'RoverType'
]