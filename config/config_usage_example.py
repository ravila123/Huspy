#!/usr/bin/env python3
"""
Example usage of the Blue Rover configuration system

This script demonstrates how to use the configuration management system
in your rover applications.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.rover_config import RoverConfig, get_config, set_config


def example_basic_usage():
    """Basic configuration usage example"""
    print("=== Basic Configuration Usage ===")
    
    # Get the global configuration (loads from files and environment)
    config = get_config()
    
    print(f"Environment: {config.environment}")
    print(f"Camera enabled: {config.camera.enabled}")
    print(f"Camera port: {config.camera.port}")
    print(f"Max speed: {config.control.max_speed}")
    print(f"Log level: {config.logging.level}")
    print()


def example_environment_specific():
    """Environment-specific configuration example"""
    print("=== Environment-Specific Configuration ===")
    
    # Load production configuration
    prod_config = RoverConfig.from_environment('production')
    print(f"Production - Debug mode: {prod_config.debug_mode}")
    print(f"Production - Camera port: {prod_config.camera.port}")
    
    # Load development configuration
    dev_config = RoverConfig.from_environment('development')
    print(f"Development - Debug mode: {dev_config.debug_mode}")
    print(f"Development - Camera port: {dev_config.camera.port}")
    print()


def example_env_variable_overrides():
    """Environment variable override example"""
    print("=== Environment Variable Overrides ===")
    
    # Set some environment variables
    os.environ['ROVER_CAMERA__PORT'] = '9999'
    os.environ['ROVER_DEBUG_MODE'] = 'true'
    os.environ['ROVER_LOGGING__LEVEL'] = 'DEBUG'
    
    # Load configuration with overrides
    config = RoverConfig.from_environment()
    
    print(f"Camera port (overridden): {config.camera.port}")
    print(f"Debug mode (overridden): {config.debug_mode}")
    print(f"Log level (overridden): {config.logging.level}")
    
    # Clean up
    del os.environ['ROVER_CAMERA__PORT']
    del os.environ['ROVER_DEBUG_MODE']
    del os.environ['ROVER_LOGGING__LEVEL']
    print()


def example_custom_config():
    """Custom configuration creation example"""
    print("=== Custom Configuration ===")
    
    # Create a custom configuration
    config = RoverConfig()
    config.camera.port = 8888
    config.control.max_speed = 75
    config.debug_mode = True
    config.environment = "testing"
    
    # Validate the configuration
    if config.validate():
        print("✓ Custom configuration is valid")
        print(f"Camera port: {config.camera.port}")
        print(f"Max speed: {config.control.max_speed}")
        print(f"Environment: {config.environment}")
    else:
        print("❌ Custom configuration is invalid")
    print()


def example_config_in_application():
    """Example of using configuration in an application"""
    print("=== Configuration in Application ===")
    
    config = get_config()
    
    # Example: Configure logging based on config
    import logging
    logging.basicConfig(level=config.get_log_level())
    logger = logging.getLogger(__name__)
    
    logger.info(f"Application starting in {config.environment} mode")
    
    # Example: Use camera settings
    if config.camera.enabled:
        logger.info(f"Camera enabled on port {config.camera.port}")
        logger.info(f"Resolution: {config.camera.resolution_width}x{config.camera.resolution_height}")
    else:
        logger.info("Camera disabled")
    
    # Example: Use control settings
    logger.info(f"Max speed set to {config.control.max_speed}%")
    logger.info(f"Steering range: ±{config.control.steering_range}°")
    
    # Example: Check environment
    if config.is_development():
        logger.debug("Running in development mode - extra debugging enabled")
    elif config.is_production():
        logger.info("Running in production mode")
    
    print()


def main():
    """Run all configuration examples"""
    print("Blue Rover Configuration System Examples\n")
    
    example_basic_usage()
    example_environment_specific()
    example_env_variable_overrides()
    example_custom_config()
    example_config_in_application()
    
    print("Examples completed!")


if __name__ == '__main__':
    main()