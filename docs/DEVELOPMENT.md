# Development Guide

This guide provides information for developers who want to contribute to or modify the Blue Rover project.

## Development Environment Setup

### Prerequisites

- Python 3.8+ (3.9+ recommended)
- Git
- Virtual environment support
- Code editor (VS Code recommended)
- Raspberry Pi for hardware testing (optional for software-only development)

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/your-username/blue-rover.git
cd blue-rover

# Create development virtual environment
python3 -m venv venv-dev
source venv-dev/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists

# Install pre-commit hooks (if configured)
pre-commit install
```

### Development Dependencies

Create `requirements-dev.txt` for development-specific packages:
```
pytest>=7.0.0
pytest-cov>=4.0.0
black>=22.0.0
flake8>=5.0.0
mypy>=0.991
pre-commit>=2.20.0
```

## Project Architecture

### Code Organization

```
src/
├── __init__.py              # Package initialization
├── blue_rover.py           # Main application entry point
├── ps5_control.py          # PS5 controller interface
├── battery_monitor.py      # Battery monitoring service
├── hardware/               # Hardware abstraction layer
│   ├── __init__.py
│   ├── rover_interface.py  # Abstract hardware interface
│   └── picarx_rover.py     # PicarX implementation
├── services/               # Background services
│   ├── __init__.py
│   ├── camera_service.py   # Camera streaming service
│   └── web_service.py      # Web interface service
└── utils/                  # Utility modules
    ├── __init__.py
    ├── logutil.py          # Logging utilities
    ├── config.py           # Configuration management
    └── validation.py       # Input validation
```

### Design Patterns

**Hardware Abstraction Layer**:
- Abstract base classes for hardware interfaces
- Factory pattern for hardware instantiation
- Dependency injection for testing

**Service Architecture**:
- Background services using systemd
- Inter-service communication via message queues
- Graceful shutdown and error recovery

**Configuration Management**:
- Centralized configuration using dataclasses
- Environment-specific overrides
- Runtime configuration validation

## Coding Standards

### Python Style Guide

Follow PEP 8 with these specific guidelines:

**Code Formatting**:
```python
# Use Black for automatic formatting
black src/ tests/

# Line length: 88 characters (Black default)
# Use double quotes for strings
# Use trailing commas in multi-line structures
```

**Import Organization**:
```python
# Standard library imports
import os
import sys
from typing import Optional, Dict, List

# Third-party imports
import pygame
import cv2
from dataclasses import dataclass

# Local imports
from src.hardware.rover_interface import RoverInterface
from src.utils.logutil import get_logger
```

**Type Hints**:
```python
# Use type hints for all public functions
def move_rover(speed: int, direction: float) -> bool:
    """Move rover with specified speed and direction.
    
    Args:
        speed: Speed value from 0-100
        direction: Direction in degrees (-90 to 90)
        
    Returns:
        True if movement successful, False otherwise
    """
    pass

# Use Optional for nullable values
def get_battery_voltage() -> Optional[float]:
    pass
```

**Error Handling**:
```python
# Use specific exception types
class RoverConnectionError(Exception):
    """Raised when rover hardware connection fails."""
    pass

# Proper exception handling
try:
    rover.connect()
except RoverConnectionError as e:
    logger.error(f"Failed to connect to rover: {e}")
    return False
```

### Documentation Standards

**Docstring Format** (Google Style):
```python
def control_camera(pan: int, tilt: int) -> bool:
    """Control camera pan and tilt position.
    
    Args:
        pan: Pan angle in degrees (-90 to 90)
        tilt: Tilt angle in degrees (-45 to 45)
        
    Returns:
        True if camera moved successfully, False otherwise
        
    Raises:
        ValueError: If angles are outside valid range
        CameraError: If camera hardware fails to respond
        
    Example:
        >>> control_camera(45, -30)
        True
    """
    pass
```

**Code Comments**:
```python
# Use comments for complex logic explanation
def calculate_motor_speeds(joystick_x: float, joystick_y: float) -> tuple[int, int]:
    # Convert joystick input to differential drive motor speeds
    # Using arcade drive algorithm for intuitive control
    forward = joystick_y * MAX_SPEED
    turn = joystick_x * MAX_TURN_RATE
    
    # Calculate individual motor speeds
    left_speed = int(forward + turn)
    right_speed = int(forward - turn)
    
    # Clamp values to valid range
    left_speed = max(-MAX_SPEED, min(MAX_SPEED, left_speed))
    right_speed = max(-MAX_SPEED, min(MAX_SPEED, right_speed))
    
    return left_speed, right_speed
```

## Testing Guidelines

### Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest configuration and fixtures
├── unit/                    # Unit tests
│   ├── test_rover_interface.py
│   ├── test_ps5_control.py
│   └── test_battery_monitor.py
├── integration/             # Integration tests
│   ├── test_hardware_integration.py
│   └── test_service_integration.py
└── fixtures/                # Test data and mock objects
    ├── mock_hardware.py
    └── test_configs.py
```

### Writing Tests

**Unit Test Example**:
```python
import pytest
from unittest.mock import Mock, patch
from src.ps5_control import PS5Controller

class TestPS5Controller:
    @pytest.fixture
    def controller(self):
        return PS5Controller()
    
    def test_controller_initialization(self, controller):
        """Test controller initializes with default values."""
        assert controller.connected is False
        assert controller.last_input is None
    
    @patch('pygame.joystick.get_count')
    def test_controller_detection(self, mock_get_count, controller):
        """Test controller detection when device is present."""
        mock_get_count.return_value = 1
        result = controller.detect_controller()
        assert result is True
    
    def test_input_validation(self, controller):
        """Test input validation for control values."""
        with pytest.raises(ValueError):
            controller.validate_input(speed=150)  # Over max speed
```

**Integration Test Example**:
```python
import pytest
from src.blue_rover import BlueRover
from tests.fixtures.mock_hardware import MockRover

class TestBlueRoverIntegration:
    @pytest.fixture
    def rover_system(self):
        return BlueRover(hardware=MockRover())
    
    def test_complete_control_flow(self, rover_system):
        """Test complete control flow from input to hardware."""
        # Simulate controller input
        rover_system.process_input({'speed': 50, 'direction': 30})
        
        # Verify hardware received correct commands
        assert rover_system.hardware.last_speed == 50
        assert rover_system.hardware.last_direction == 30
```

### Test Fixtures

**Mock Hardware**:
```python
# tests/fixtures/mock_hardware.py
from src.hardware.rover_interface import RoverInterface

class MockRover(RoverInterface):
    """Mock rover for testing without hardware."""
    
    def __init__(self):
        self.connected = False
        self.last_speed = 0
        self.last_direction = 0
        self.battery_voltage = 7.4
    
    def connect(self) -> bool:
        self.connected = True
        return True
    
    def move_forward(self, speed: int) -> None:
        self.last_speed = speed
    
    def set_steering(self, angle: int) -> None:
        self.last_direction = angle
    
    def get_battery_voltage(self) -> float:
        return self.battery_voltage
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_ps5_control.py

# Run tests with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_controller"
```

## Contributing Guidelines

### Git Workflow

**Branch Naming**:
- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `hotfix/description` - Critical fixes
- `docs/description` - Documentation updates

**Commit Messages**:
```
feat: add PS5 controller haptic feedback support

- Implement rumble feedback for collision detection
- Add configuration options for feedback intensity
- Update controller interface documentation

Closes #123
```

**Pull Request Process**:
1. Create feature branch from `main`
2. Implement changes with tests
3. Update documentation if needed
4. Run full test suite
5. Create pull request with detailed description
6. Address review feedback
7. Squash commits before merge

### Code Review Checklist

**Functionality**:
- [ ] Code works as intended
- [ ] Edge cases handled appropriately
- [ ] Error handling implemented
- [ ] Performance considerations addressed

**Code Quality**:
- [ ] Follows project coding standards
- [ ] Proper type hints used
- [ ] Comprehensive docstrings
- [ ] No code duplication

**Testing**:
- [ ] Unit tests cover new functionality
- [ ] Integration tests updated if needed
- [ ] All tests pass
- [ ] Test coverage maintained or improved

**Documentation**:
- [ ] README updated if needed
- [ ] API documentation current
- [ ] Comments explain complex logic
- [ ] Examples provided for new features

## Debugging and Development Tools

### Logging Configuration

```python
# Development logging setup
import logging
from src.utils.logutil import setup_logging

# Enable debug logging during development
setup_logging(level=logging.DEBUG, console=True)

# Use structured logging for better debugging
logger = logging.getLogger(__name__)
logger.debug("Controller input received", extra={
    'speed': speed,
    'direction': direction,
    'timestamp': time.time()
})
```

### Remote Debugging

**SSH Development**:
```bash
# Forward ports for web interface testing
ssh -L 8080:localhost:8080 pi@rover-ip

# Remote Python debugging with pdb
python3 -m pdb src/blue_rover.py
```

**VS Code Remote Development**:
1. Install Remote-SSH extension
2. Connect to Raspberry Pi
3. Open Blue Rover project remotely
4. Use integrated debugging tools

### Hardware Simulation

**Mock Hardware for Development**:
```python
# Use mock hardware when not on Pi
if platform.system() != 'Linux' or not os.path.exists('/dev/gpiomem'):
    from tests.fixtures.mock_hardware import MockRover
    hardware = MockRover()
else:
    from src.hardware.picarx_rover import PicarXRover
    hardware = PicarXRover()
```

## Performance Optimization

### Profiling

```bash
# Profile application performance
python3 -m cProfile -o profile.stats src/blue_rover.py

# Analyze profile results
python3 -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats(20)"
```

### Memory Management

```python
# Monitor memory usage
import tracemalloc

tracemalloc.start()

# Your code here

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.1f} MB")
```

### Optimization Guidelines

**Control Loop Performance**:
- Target 50Hz update rate for responsive control
- Use efficient data structures
- Minimize memory allocations in loops
- Profile critical paths regularly

**Network Optimization**:
- Compress video streams appropriately
- Use efficient serialization for control data
- Implement connection pooling where applicable
- Monitor bandwidth usage

## Release Process

### Version Management

Use semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features, backward compatible
- PATCH: Bug fixes, backward compatible

### Release Checklist

**Pre-release**:
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version number incremented
- [ ] Changelog updated
- [ ] Performance benchmarks run

**Release**:
- [ ] Create release branch
- [ ] Tag release version
- [ ] Build and test release package
- [ ] Update GitHub release notes
- [ ] Merge to main branch

**Post-release**:
- [ ] Monitor for issues
- [ ] Update documentation site
- [ ] Announce release
- [ ] Plan next iteration

## Security Considerations

### Code Security

**Input Validation**:
```python
def validate_speed(speed: int) -> int:
    """Validate and clamp speed input."""
    if not isinstance(speed, int):
        raise TypeError("Speed must be an integer")
    return max(-100, min(100, speed))
```

**Secure Configuration**:
- Never commit secrets or passwords
- Use environment variables for sensitive data
- Implement proper access controls
- Validate all external inputs

### Deployment Security

- Use SSH keys instead of passwords
- Keep system packages updated
- Implement firewall rules
- Monitor system logs for anomalies

## Getting Help

### Development Resources

- **Project Wiki**: Detailed technical documentation
- **API Reference**: Generated from docstrings
- **Example Code**: See `examples/` directory
- **Issue Tracker**: Report bugs and request features

### Community

- **Discussions**: GitHub Discussions for questions
- **Code Review**: Pull request reviews
- **Mentoring**: Pair programming sessions available
- **Documentation**: Help improve project documentation

### Contribution Recognition

Contributors are recognized through:
- GitHub contributor statistics
- Release notes acknowledgments
- Project documentation credits
- Community showcase features