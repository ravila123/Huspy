#!/usr/bin/env python3
"""
Hardware Testing Suite

Tests the hardware abstraction layer including:
- Mock rover implementation
- PicarX rover implementation (when available)
- Hardware factory functionality
- Hardware detection and validation

Requirements: 6.1, 6.2, 6.4
"""

import unittest
import sys
import pathlib
import tempfile
import time
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from hardware.rover_interface import RoverInterface, RoverCapabilities, RoverStatus
from hardware.mock_rover import MockRover
from hardware.hardware_factory import HardwareFactory, RoverType
from hardware.picarx_rover import PicarXRover


class TestRoverInterface(unittest.TestCase):
    """Test the abstract rover interface"""
    
    def test_rover_capabilities_enum(self):
        """Test rover capabilities enumeration"""
        capabilities = list(RoverCapabilities)
        expected_capabilities = [
            RoverCapabilities.MOVEMENT,
            RoverCapabilities.STEERING,
            RoverCapabilities.CAMERA_PAN_TILT,
            RoverCapabilities.BATTERY_MONITORING,
            RoverCapabilities.CAMERA_CAPTURE,
            RoverCapabilities.CAMERA_STREAMING
        ]
        
        for cap in expected_capabilities:
            self.assertIn(cap, capabilities)
    
    def test_rover_status_dataclass(self):
        """Test rover status data structure"""
        status = RoverStatus()
        
        # Test default values
        self.assertEqual(status.speed, 0)
        self.assertEqual(status.direction, 1)
        self.assertEqual(status.steering_angle, 0)
        self.assertEqual(status.camera_pan, 0)
        self.assertEqual(status.camera_tilt, 0)
        self.assertIsNone(status.battery_voltage)
        self.assertFalse(status.is_connected)
        self.assertIsNone(status.error_message)
        
        # Test custom values
        status = RoverStatus(
            speed=50,
            direction=-1,
            steering_angle=15,
            battery_voltage=7.4,
            is_connected=True,
            error_message="Test error"
        )
        
        self.assertEqual(status.speed, 50)
        self.assertEqual(status.direction, -1)
        self.assertEqual(status.steering_angle, 15)
        self.assertEqual(status.battery_voltage, 7.4)
        self.assertTrue(status.is_connected)
        self.assertEqual(status.error_message, "Test error")


class TestMockRover(unittest.TestCase):
    """Test mock rover implementation"""
    
    def setUp(self):
        """Set up test environment"""
        self.rover = MockRover(
            simulate_battery_drain=False,
            initial_battery_voltage=8.0,
            connection_reliability=1.0  # 100% reliable for testing
        )
    
    def tearDown(self):
        """Clean up test environment"""
        if self.rover.is_connected():
            self.rover.shutdown()
    
    def test_mock_rover_initialization(self):
        """Test mock rover initialization"""
        self.assertFalse(self.rover.is_connected())
        
        # Test successful initialization
        self.assertTrue(self.rover.initialize())
        self.assertTrue(self.rover.is_connected())
        
        # Check capabilities
        expected_capabilities = {
            RoverCapabilities.MOVEMENT,
            RoverCapabilities.STEERING,
            RoverCapabilities.CAMERA_PAN_TILT,
            RoverCapabilities.BATTERY_MONITORING,
            RoverCapabilities.CAMERA_CAPTURE,
            RoverCapabilities.CAMERA_STREAMING
        }
        self.assertEqual(self.rover.capabilities, expected_capabilities)
    
    def test_mock_rover_movement(self):
        """Test mock rover movement commands"""
        self.rover.initialize()
        
        # Test forward movement
        self.assertTrue(self.rover.move_forward(50))
        self.assertEqual(self.rover.status.speed, 50)
        self.assertEqual(self.rover.status.direction, 1)
        
        # Test backward movement
        self.assertTrue(self.rover.move_backward(30))
        self.assertEqual(self.rover.status.speed, 30)
        self.assertEqual(self.rover.status.direction, -1)
        
        # Test stop
        self.assertTrue(self.rover.stop())
        self.assertEqual(self.rover.status.speed, 0)
        self.assertEqual(self.rover.status.direction, 0)
        
        # Test speed clamping
        self.assertTrue(self.rover.move_forward(150))  # Over 100
        self.assertEqual(self.rover.status.speed, 100)
        
        self.assertTrue(self.rover.move_backward(-10))  # Negative
        self.assertEqual(self.rover.status.speed, 0)
    
    def test_mock_rover_steering(self):
        """Test mock rover steering"""
        self.rover.initialize()
        
        # Test steering
        self.assertTrue(self.rover.set_steering_angle(20))
        self.assertEqual(self.rover.status.steering_angle, 20)
        
        # Test angle clamping
        self.assertTrue(self.rover.set_steering_angle(50))  # Over 35
        self.assertEqual(self.rover.status.steering_angle, 35)
        
        self.assertTrue(self.rover.set_steering_angle(-50))  # Under -35
        self.assertEqual(self.rover.status.steering_angle, -35)
        
        # Test center steering
        self.assertTrue(self.rover.center_steering())
        self.assertEqual(self.rover.status.steering_angle, 0)
    
    def test_mock_rover_camera(self):
        """Test mock rover camera control"""
        self.rover.initialize()
        
        # Test camera pan
        self.assertTrue(self.rover.set_camera_pan(15))
        self.assertEqual(self.rover.status.camera_pan, 15)
        
        # Test camera tilt
        self.assertTrue(self.rover.set_camera_tilt(-10))
        self.assertEqual(self.rover.status.camera_tilt, -10)
        
        # Test camera position
        self.assertTrue(self.rover.set_camera_position(25, -20))
        self.assertEqual(self.rover.status.camera_pan, 25)
        self.assertEqual(self.rover.status.camera_tilt, -20)
        
        # Test center camera
        self.assertTrue(self.rover.center_camera())
        self.assertEqual(self.rover.status.camera_pan, 0)
        self.assertEqual(self.rover.status.camera_tilt, 0)
    
    def test_mock_rover_battery(self):
        """Test mock rover battery monitoring"""
        self.rover.initialize()
        
        voltage = self.rover.get_battery_voltage()
        self.assertIsNotNone(voltage)
        self.assertGreater(voltage, 5.0)  # Reasonable voltage
        self.assertLess(voltage, 12.0)
    
    def test_mock_rover_photo_capture(self):
        """Test mock rover photo capture"""
        self.rover.initialize()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test photo capture
            self.assertTrue(self.rover.take_photo("test_photo", temp_dir))
            
            # Check if file was created
            photo_path = pathlib.Path(temp_dir) / "test_photo.jpg"
            self.assertTrue(photo_path.exists())
            self.assertGreater(photo_path.stat().st_size, 0)
    
    def test_mock_rover_reliability_simulation(self):
        """Test mock rover connection reliability simulation"""
        # Create rover with low reliability
        unreliable_rover = MockRover(connection_reliability=0.0)  # 0% reliable
        unreliable_rover.initialize()
        
        # Most operations should fail
        failures = 0
        attempts = 10
        
        for _ in range(attempts):
            if not unreliable_rover.move_forward(50):
                failures += 1
        
        # Should have some failures (not necessarily all due to randomness)
        self.assertGreater(failures, 0)
        
        unreliable_rover.shutdown()
    
    def test_mock_rover_disconnection_simulation(self):
        """Test mock rover disconnection simulation"""
        self.rover.initialize()
        self.assertTrue(self.rover.is_connected())
        
        # Simulate disconnection
        self.rover.simulate_disconnection()
        self.assertFalse(self.rover.is_connected())
        
        # Operations should fail when disconnected
        self.assertFalse(self.rover.move_forward(50))
        self.assertFalse(self.rover.set_steering_angle(10))
        
        # Test reconnection
        self.assertTrue(self.rover.simulate_reconnection())
        self.assertTrue(self.rover.is_connected())
        
        # Operations should work again
        self.assertTrue(self.rover.move_forward(50))
    
    def test_mock_rover_emergency_stop(self):
        """Test mock rover emergency stop"""
        self.rover.initialize()
        
        # Set rover in motion with steering
        self.rover.move_forward(75)
        self.rover.set_steering_angle(20)
        
        # Emergency stop
        self.assertTrue(self.rover.emergency_stop())
        
        # Should be stopped and centered
        self.assertEqual(self.rover.status.speed, 0)
        self.assertEqual(self.rover.status.direction, 0)
        self.assertEqual(self.rover.status.steering_angle, 0)
    
    def test_mock_rover_status_summary(self):
        """Test mock rover status summary"""
        self.rover.initialize()
        
        # Test disconnected status
        self.rover.simulate_disconnection()
        summary = self.rover.get_status_summary()
        self.assertIn("Disconnected", summary)
        
        # Test connected status
        self.rover.simulate_reconnection()
        self.rover.move_forward(50)
        self.rover.set_steering_angle(15)
        
        summary = self.rover.get_status_summary()
        self.assertIn("Forward", summary)
        self.assertIn("50%", summary)
        self.assertIn("15°", summary)


class TestHardwareFactory(unittest.TestCase):
    """Test hardware factory functionality"""
    
    def test_create_mock_rover(self):
        """Test creating mock rover through factory"""
        rover = HardwareFactory.create_rover(RoverType.MOCK, connection_reliability=1.0)
        
        self.assertIsInstance(rover, MockRover)
        self.assertIsInstance(rover, RoverInterface)
        
        # Test initialization
        self.assertTrue(rover.initialize())
        self.assertTrue(rover.is_connected())
        
        rover.shutdown()
    
    def test_create_rover_with_config(self):
        """Test creating rover with configuration"""
        config = {
            'rover_type': 'mock',
            'rover_config': {
                'connection_reliability': 1.0,  # Set to 100% for reliable testing
                'initial_battery_voltage': 7.5
            }
        }
        
        rover = HardwareFactory.create_rover_from_config(config)
        self.assertIsInstance(rover, MockRover)
        
        rover.initialize()
        voltage = rover.get_battery_voltage()
        self.assertIsNotNone(voltage, "Battery voltage should not be None")
        self.assertAlmostEqual(voltage, 7.5, delta=0.5)  # Allow for variation
        
        rover.shutdown()
    
    def test_get_available_rover_types(self):
        """Test getting available rover types"""
        available_types = HardwareFactory.get_available_rover_types()
        
        # Mock should always be available
        self.assertIn(RoverType.MOCK, available_types)
        self.assertIn(RoverType.AUTO, available_types)
    
    def test_hardware_detection(self):
        """Test hardware detection"""
        detection_results = HardwareFactory.detect_hardware()
        
        # Should return a dictionary with expected keys
        expected_keys = [
            'picarx_available',
            'camera_available', 
            'recommended_type',
            'detection_errors'
        ]
        
        for key in expected_keys:
            self.assertIn(key, detection_results)
        
        # Should recommend a valid rover type
        self.assertIsInstance(detection_results['recommended_type'], RoverType)
    
    def test_auto_rover_creation(self):
        """Test automatic rover creation"""
        rover = HardwareFactory.create_rover(RoverType.AUTO)
        
        # Should create some type of rover
        self.assertIsInstance(rover, RoverInterface)
        
        # Should be able to initialize (may be mock rover)
        init_result = rover.initialize()
        if not init_result:
            # If initialization fails, it might be due to simulated failure
            # Try again or check if it's a mock rover with low reliability
            if isinstance(rover, MockRover):
                rover.set_connection_reliability(1.0)  # Set to 100% for testing
                init_result = rover.initialize()
        
        self.assertTrue(init_result, "Auto rover should initialize successfully")
        
        rover.shutdown()
    
    def test_invalid_rover_type(self):
        """Test handling of invalid rover type"""
        with self.assertRaises(RuntimeError):
            # This should raise RuntimeError for unsupported type
            HardwareFactory.create_rover("invalid_type")
    
    def test_convenience_functions(self):
        """Test convenience functions"""
        # Test create_mock_rover
        from hardware.hardware_factory import create_mock_rover
        rover = create_mock_rover(connection_reliability=0.9)
        self.assertIsInstance(rover, MockRover)
        rover.shutdown()
        
        # Test create_auto_rover
        from hardware.hardware_factory import create_auto_rover
        rover = create_auto_rover()
        self.assertIsInstance(rover, RoverInterface)
        rover.shutdown()


class TestPicarXRover(unittest.TestCase):
    """Test PicarX rover implementation (with mocking)"""
    
    def setUp(self):
        """Set up test environment with mocked hardware"""
        # Mock the hardware imports
        self.picarx_mock = MagicMock()
        self.vilib_mock = MagicMock()
        
        # Patch the imports
        self.picarx_patcher = patch('hardware.picarx_rover.Picarx', return_value=self.picarx_mock)
        self.vilib_patcher = patch('hardware.picarx_rover.Vilib', self.vilib_mock)
        self.hardware_available_patcher = patch('hardware.picarx_rover.HARDWARE_AVAILABLE', True)
        
        self.picarx_patcher.start()
        self.vilib_patcher.start()
        self.hardware_available_patcher.start()
        
        self.rover = PicarXRover(camera_enabled=True)
    
    def tearDown(self):
        """Clean up test environment"""
        self.picarx_patcher.stop()
        self.vilib_patcher.stop()
        self.hardware_available_patcher.stop()
        
        if self.rover.is_connected():
            self.rover.shutdown()
    
    def test_picarx_initialization(self):
        """Test PicarX rover initialization"""
        self.assertFalse(self.rover.is_connected())
        
        # Test successful initialization
        self.assertTrue(self.rover.initialize())
        self.assertTrue(self.rover.is_connected())
        
        # Verify hardware calls
        self.vilib_mock.camera_start.assert_called_once()
        self.vilib_mock.display.assert_called_once()
        
        # Verify centering calls
        self.picarx_mock.set_dir_servo_angle.assert_called_with(0)
        self.picarx_mock.set_cam_pan_angle.assert_called_with(0)
        self.picarx_mock.set_cam_tilt_angle.assert_called_with(0)
    
    def test_picarx_movement_commands(self):
        """Test PicarX movement commands"""
        self.rover.initialize()
        
        # Test forward movement
        self.assertTrue(self.rover.move_forward(50))
        self.picarx_mock.forward.assert_called_with(50)
        self.assertEqual(self.rover.status.speed, 50)
        self.assertEqual(self.rover.status.direction, 1)
        
        # Test backward movement
        self.assertTrue(self.rover.move_backward(30))
        self.picarx_mock.backward.assert_called_with(30)
        self.assertEqual(self.rover.status.speed, 30)
        self.assertEqual(self.rover.status.direction, -1)
        
        # Test stop
        self.assertTrue(self.rover.stop())
        self.picarx_mock.stop.assert_called_once()
        self.assertEqual(self.rover.status.speed, 0)
        self.assertEqual(self.rover.status.direction, 0)
    
    def test_picarx_steering_commands(self):
        """Test PicarX steering commands"""
        self.rover.initialize()
        
        # Test steering
        self.assertTrue(self.rover.set_steering_angle(20))
        self.picarx_mock.set_dir_servo_angle.assert_called_with(20)
        self.assertEqual(self.rover.status.steering_angle, 20)
        
        # Test angle clamping
        self.assertTrue(self.rover.set_steering_angle(50))
        self.picarx_mock.set_dir_servo_angle.assert_called_with(35)  # Clamped
        self.assertEqual(self.rover.status.steering_angle, 35)
    
    def test_picarx_camera_commands(self):
        """Test PicarX camera commands"""
        self.rover.initialize()
        
        # Test camera pan
        self.assertTrue(self.rover.set_camera_pan(15))
        self.picarx_mock.set_cam_pan_angle.assert_called_with(15)
        self.assertEqual(self.rover.status.camera_pan, 15)
        
        # Test camera tilt
        self.assertTrue(self.rover.set_camera_tilt(-10))
        self.picarx_mock.set_cam_tilt_angle.assert_called_with(-10)
        self.assertEqual(self.rover.status.camera_tilt, -10)
        
        # Test camera position (optimized method)
        self.assertTrue(self.rover.set_camera_position(25, -20))
        self.picarx_mock.set_cam_pan_angle.assert_called_with(25)
        self.picarx_mock.set_cam_tilt_angle.assert_called_with(-20)
    
    def test_picarx_battery_monitoring(self):
        """Test PicarX battery monitoring"""
        self.rover.initialize()
        
        # Mock battery voltage return
        self.picarx_mock.get_battery_voltage.return_value = 7.4
        
        voltage = self.rover.get_battery_voltage()
        self.assertEqual(voltage, 7.4)
        self.assertEqual(self.rover.status.battery_voltage, 7.4)
    
    def test_picarx_photo_capture(self):
        """Test PicarX photo capture"""
        self.rover.initialize()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock successful photo capture
            photo_path = pathlib.Path(temp_dir) / "test_photo.jpg"
            
            # Create a mock photo file that Vilib.take_photo would create
            def mock_take_photo(filename, path):
                (pathlib.Path(path) / f"{filename}.jpg").touch()
            
            self.vilib_mock.take_photo.side_effect = mock_take_photo
            
            # Test photo capture
            self.assertTrue(self.rover.take_photo("test_photo", temp_dir))
            self.vilib_mock.take_photo.assert_called_with("test_photo", temp_dir + "/")
            self.assertTrue(photo_path.exists())
    
    def test_picarx_shutdown(self):
        """Test PicarX shutdown"""
        self.rover.initialize()
        
        self.rover.shutdown()
        
        # Verify shutdown calls
        self.picarx_mock.stop.assert_called()
        self.picarx_mock.set_dir_servo_angle.assert_called_with(0)
        self.picarx_mock.set_cam_pan_angle.assert_called_with(0)
        self.picarx_mock.set_cam_tilt_angle.assert_called_with(0)
        self.vilib_mock.camera_close.assert_called_once()
        
        self.assertFalse(self.rover.is_connected())
    
    def test_picarx_hardware_unavailable(self):
        """Test PicarX behavior when hardware is unavailable"""
        # Stop the hardware available patch
        self.hardware_available_patcher.stop()
        
        with patch('hardware.picarx_rover.HARDWARE_AVAILABLE', False):
            rover = PicarXRover()
            
            # Initialization should fail gracefully
            self.assertFalse(rover.initialize())
            self.assertFalse(rover.is_connected())
            self.assertIsNotNone(rover.status.error_message)
        
        # Restart the patch for tearDown
        self.hardware_available_patcher.start()


class TestHardwareIntegration(unittest.TestCase):
    """Integration tests for hardware components"""
    
    def test_rover_interface_compliance(self):
        """Test that all rover implementations comply with interface"""
        rovers = [
            MockRover(),
            # PicarXRover would be tested here if hardware is available
        ]
        
        for rover in rovers:
            with self.subTest(rover=rover.__class__.__name__):
                # Test interface compliance
                self.assertIsInstance(rover, RoverInterface)
                
                # Test required methods exist
                required_methods = [
                    'initialize', 'shutdown', 'is_connected',
                    'move_forward', 'move_backward', 'stop',
                    'set_steering_angle', 'set_camera_pan', 'set_camera_tilt',
                    'get_battery_voltage', 'take_photo'
                ]
                
                for method in required_methods:
                    self.assertTrue(hasattr(rover, method))
                    self.assertTrue(callable(getattr(rover, method)))
                
                # Test basic lifecycle
                self.assertTrue(rover.initialize())
                self.assertTrue(rover.is_connected())
                rover.shutdown()
                self.assertFalse(rover.is_connected())
    
    def test_hardware_factory_integration(self):
        """Test hardware factory integration with different rover types"""
        # Test mock rover creation
        mock_rover = HardwareFactory.create_rover(RoverType.MOCK)
        self.assertIsInstance(mock_rover, MockRover)
        mock_rover.initialize()
        self.assertTrue(mock_rover.is_connected())
        mock_rover.shutdown()
        
        # Test auto rover creation (should fall back to mock)
        auto_rover = HardwareFactory.create_rover(RoverType.AUTO)
        self.assertIsInstance(auto_rover, RoverInterface)
        auto_rover.initialize()
        self.assertTrue(auto_rover.is_connected())
        auto_rover.shutdown()
    
    def test_capability_checking(self):
        """Test capability checking across rover implementations"""
        rover = MockRover()
        rover.initialize()
        
        # Test capability checking
        self.assertTrue(rover.has_capability(RoverCapabilities.MOVEMENT))
        self.assertTrue(rover.has_capability(RoverCapabilities.CAMERA_CAPTURE))
        
        # Test capabilities property
        capabilities = rover.capabilities
        self.assertIsInstance(capabilities, set)
        self.assertIn(RoverCapabilities.MOVEMENT, capabilities)
        
        rover.shutdown()


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2, buffer=True)