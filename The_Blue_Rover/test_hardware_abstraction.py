#!/usr/bin/env python3
"""
Test script for hardware abstraction layer

Simple test to verify that the hardware abstraction layer works correctly
with both mock and PicarX implementations.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from hardware import HardwareFactory, RoverType, RoverCapabilities


def test_mock_rover():
    """Test mock rover implementation"""
    print("Testing Mock Rover Implementation")
    print("=" * 40)
    
    try:
        # Create mock rover with high reliability for testing
        rover = HardwareFactory.create_rover(RoverType.MOCK, connection_reliability=1.0)
        
        print(f"Rover capabilities: {[cap.value for cap in rover.capabilities]}")
        print(f"Has movement capability: {rover.has_capability(RoverCapabilities.MOVEMENT)}")
        
        # Initialize
        if rover.initialize():
            print("✓ Rover initialized successfully")
        else:
            print("✗ Rover initialization failed")
            return False
        
        print(f"Connection status: {rover.is_connected()}")
        print(f"Status: {rover.get_status_summary()}")
        
        # Test movement
        print("\nTesting movement commands:")
        if rover.move_forward(50):
            print("✓ Forward movement successful")
        else:
            print("✗ Forward movement failed")
        
        print(f"Status: {rover.get_status_summary()}")
        
        # Test steering
        if rover.set_steering_angle(15):
            print("✓ Steering successful")
        else:
            print("✗ Steering failed")
        
        # Test camera
        if rover.set_camera_position(10, -5):
            print("✓ Camera positioning successful")
        else:
            print("✗ Camera positioning failed")
        
        print(f"Status: {rover.get_status_summary()}")
        
        # Test battery
        voltage = rover.get_battery_voltage()
        if voltage is not None:
            print(f"✓ Battery voltage: {voltage:.2f}V")
        else:
            print("✗ Battery voltage reading failed")
        
        # Test photo
        if rover.take_photo("test_photo", "logs"):
            print("✓ Photo capture successful")
        else:
            print("✗ Photo capture failed")
        
        # Test emergency stop
        if rover.emergency_stop():
            print("✓ Emergency stop successful")
        else:
            print("✗ Emergency stop failed")
        
        print(f"Final status: {rover.get_status_summary()}")
        
        # Shutdown
        rover.shutdown()
        print("✓ Rover shutdown complete")
        
        return True
        
    except Exception as e:
        print(f"✗ Mock rover test failed: {e}")
        return False


def test_hardware_factory():
    """Test hardware factory functionality"""
    print("\nTesting Hardware Factory")
    print("=" * 40)
    
    try:
        # Test available types
        available_types = HardwareFactory.get_available_rover_types()
        print(f"Available rover types: {[t.value for t in available_types]}")
        
        # Test hardware detection
        detection = HardwareFactory.detect_hardware()
        print(f"Hardware detection results:")
        for key, value in detection.items():
            print(f"  {key}: {value}")
        
        # Test auto-detection
        print("\nTesting auto-detection:")
        rover = HardwareFactory.create_rover(RoverType.AUTO)
        print(f"Auto-detected rover type: {type(rover).__name__}")
        
        if rover.initialize():
            print("✓ Auto-detected rover initialized")
            print(f"Status: {rover.get_status_summary()}")
            rover.shutdown()
        else:
            print("✗ Auto-detected rover initialization failed")
        
        return True
        
    except Exception as e:
        print(f"✗ Hardware factory test failed: {e}")
        return False


def test_config_creation():
    """Test rover creation from configuration"""
    print("\nTesting Configuration-based Creation")
    print("=" * 40)
    
    try:
        config = {
            'rover_type': 'mock',
            'rover_config': {
                'connection_reliability': 0.8,
                'initial_battery_voltage': 7.5
            }
        }
        
        rover = HardwareFactory.create_rover_from_config(config)
        print(f"Created rover from config: {type(rover).__name__}")
        
        if rover.initialize():
            voltage = rover.get_battery_voltage()
            print(f"✓ Config-based rover initialized, battery: {voltage:.2f}V")
            rover.shutdown()
            return True
        else:
            print("✗ Config-based rover initialization failed")
            return False
            
    except Exception as e:
        print(f"✗ Config-based creation test failed: {e}")
        return False


def main():
    """Run all tests"""
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("Hardware Abstraction Layer Test")
    print("=" * 50)
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    tests = [
        test_mock_rover,
        test_hardware_factory,
        test_config_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("✓ PASSED\n")
            else:
                print("✗ FAILED\n")
        except Exception as e:
            print(f"✗ FAILED with exception: {e}\n")
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())