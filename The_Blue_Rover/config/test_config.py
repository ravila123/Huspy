#!/usr/bin/env python3
"""
Test script for rover configuration system
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.rover_config import RoverConfig, get_config, set_config, reload_config


def test_default_config():
    """Test default configuration creation"""
    print("Testing default configuration...")
    config = RoverConfig()
    
    assert config.camera.enabled == True
    assert config.camera.port == 8080
    assert config.control.max_speed == 100
    assert config.battery.check_interval == 5
    assert config.logging.level == "INFO"
    assert config.environment == "production"
    
    print("✓ Default configuration test passed")


def test_config_validation():
    """Test configuration validation"""
    print("Testing configuration validation...")
    
    # Valid configuration
    config = RoverConfig()
    assert config.validate() == True
    
    # Invalid configuration
    config.camera.port = 70000  # Invalid port
    config.control.max_speed = 150  # Invalid speed
    assert config.validate() == False
    
    print("✓ Configuration validation test passed")


def test_json_loading():
    """Test JSON configuration loading"""
    print("Testing JSON configuration loading...")
    
    # Test loading existing config file
    if Path('config/rover_config.json').exists():
        config = RoverConfig.from_file('config/rover_config.json')
        assert config.camera.port == 8080
        assert config.environment == "production"
        print("✓ JSON loading test passed")
    else:
        print("⚠ Skipping JSON loading test - config file not found")


def test_environment_overrides():
    """Test environment-specific configuration"""
    print("Testing environment configuration...")
    
    # Test development environment
    if Path('config/rover_config_development.json').exists():
        config = RoverConfig.from_environment('development')
        assert config.environment == "development"
        assert config.debug_mode == True
        assert config.camera.port == 8081  # Override from dev config
        print("✓ Environment configuration test passed")
    else:
        print("⚠ Skipping environment test - dev config file not found")


def test_env_variable_overrides():
    """Test environment variable overrides"""
    print("Testing environment variable overrides...")
    
    # Set environment variables
    os.environ['ROVER_CAMERA__PORT'] = '9090'
    os.environ['ROVER_DEBUG_MODE'] = 'true'
    os.environ['ROVER_CONTROL__MAX_SPEED'] = '75'
    
    config = RoverConfig.from_environment()
    
    assert config.camera.port == 9090
    assert config.debug_mode == True
    assert config.control.max_speed == 75
    
    # Clean up environment variables
    del os.environ['ROVER_CAMERA__PORT']
    del os.environ['ROVER_DEBUG_MODE']
    del os.environ['ROVER_CONTROL__MAX_SPEED']
    
    print("✓ Environment variable override test passed")


def test_config_saving():
    """Test configuration saving"""
    print("Testing configuration saving...")
    
    config = RoverConfig()
    config.camera.port = 8888
    config.debug_mode = True
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        config.to_file(temp_path, 'json')
        
        # Load it back
        loaded_config = RoverConfig.from_file(temp_path)
        assert loaded_config.camera.port == 8888
        assert loaded_config.debug_mode == True
        
        print("✓ Configuration saving test passed")
    finally:
        os.unlink(temp_path)


def test_global_config():
    """Test global configuration instance"""
    print("Testing global configuration...")
    
    # Test default global config
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2  # Should be same instance
    
    # Test setting custom config
    custom_config = RoverConfig()
    custom_config.camera.port = 7777
    set_config(custom_config)
    
    config3 = get_config()
    assert config3.camera.port == 7777
    
    print("✓ Global configuration test passed")


def main():
    """Run all configuration tests"""
    print("Running rover configuration tests...\n")
    
    try:
        test_default_config()
        test_config_validation()
        test_json_loading()
        test_environment_overrides()
        test_env_variable_overrides()
        test_config_saving()
        test_global_config()
        
        print("\n🎉 All configuration tests passed!")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())