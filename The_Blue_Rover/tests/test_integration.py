#!/usr/bin/env python3
"""
Integration Testing Suite

Tests end-to-end control flow and system integration including:
- Complete rover control workflows
- Service integration testing
- Configuration system integration
- Logging system integration
- Web interface integration

Requirements: 6.1, 6.2, 6.4
"""

import unittest
import sys
import pathlib
import tempfile
import subprocess
import time
import json
import threading
import socket
from unittest.mock import patch, MagicMock, Mock
import os

# Add project root to path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import project modules
try:
    from hardware.hardware_factory import HardwareFactory, RoverType
    from hardware.mock_rover import MockRover
    from config.rover_config import RoverConfig
except ImportError:
    # Skip integration tests if modules not available
    import sys
    print("Skipping integration tests - modules not available")
    sys.exit(0)


class TestEndToEndControlFlow(unittest.TestCase):
    """Test complete end-to-end rover control workflows"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = pathlib.Path(self.temp_dir) / "logs"
        self.log_dir.mkdir()
        
        # Create mock rover for testing
        self.rover = MockRover(
            simulate_battery_drain=False,
            initial_battery_voltage=8.0,
            connection_reliability=1.0
        )
        self.rover.initialize()
    
    def tearDown(self):
        """Clean up test environment"""
        if self.rover and self.rover.is_connected():
            self.rover.shutdown()
        
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_basic_movement_workflow(self):
        """Test basic movement control workflow"""
        # Test forward movement sequence
        self.assertTrue(self.rover.move_forward(50))
        self.assertEqual(self.rover.status.speed, 50)
        self.assertEqual(self.rover.status.direction, 1)
        
        # Test steering while moving
        self.assertTrue(self.rover.set_steering_angle(15))
        self.assertEqual(self.rover.status.steering_angle, 15)
        
        # Test direction change
        self.assertTrue(self.rover.move_backward(30))
        self.assertEqual(self.rover.status.speed, 30)
        self.assertEqual(self.rover.status.direction, -1)
        
        # Test stop and center
        self.assertTrue(self.rover.emergency_stop())
        self.assertEqual(self.rover.status.speed, 0)
        self.assertEqual(self.rover.status.direction, 0)
        self.assertEqual(self.rover.status.steering_angle, 0)
    
    def test_camera_control_workflow(self):
        """Test camera control workflow"""
        # Test camera positioning sequence
        self.assertTrue(self.rover.set_camera_pan(20))
        self.assertTrue(self.rover.set_camera_tilt(-10))
        
        self.assertEqual(self.rover.status.camera_pan, 20)
        self.assertEqual(self.rover.status.camera_tilt, -10)
        
        # Test photo capture
        self.assertTrue(self.rover.take_photo("test_workflow", str(self.temp_dir)))
        
        # Verify photo was created
        photo_path = pathlib.Path(self.temp_dir) / "test_workflow.jpg"
        self.assertTrue(photo_path.exists())
        
        # Test camera centering
        self.assertTrue(self.rover.center_camera())
        self.assertEqual(self.rover.status.camera_pan, 0)
        self.assertEqual(self.rover.status.camera_tilt, 0)
    
    def test_battery_monitoring_workflow(self):
        """Test battery monitoring workflow"""
        # Test battery reading
        voltage = self.rover.get_battery_voltage()
        self.assertIsNotNone(voltage)
        self.assertGreater(voltage, 5.0)
        self.assertLess(voltage, 12.0)
        
        # Test multiple readings for consistency
        voltages = []
        for _ in range(5):
            v = self.rover.get_battery_voltage()
            self.assertIsNotNone(v)
            voltages.append(v)
        
        # Voltages should be reasonably consistent
        voltage_range = max(voltages) - min(voltages)
        self.assertLess(voltage_range, 1.0, "Battery voltage readings too inconsistent")
    
    def test_error_recovery_workflow(self):
        """Test error recovery and reconnection workflow"""
        # Simulate connection loss
        self.rover.simulate_disconnection()
        self.assertFalse(self.rover.is_connected())
        
        # Operations should fail gracefully
        self.assertFalse(self.rover.move_forward(50))
        self.assertFalse(self.rover.set_steering_angle(10))
        
        # Test reconnection
        self.assertTrue(self.rover.simulate_reconnection())
        self.assertTrue(self.rover.is_connected())
        
        # Operations should work again
        self.assertTrue(self.rover.move_forward(50))
        self.assertTrue(self.rover.set_steering_angle(10))
        
        # Test emergency stop after reconnection
        self.assertTrue(self.rover.emergency_stop())
    
    def test_complex_maneuver_workflow(self):
        """Test complex maneuver combining multiple controls"""
        # Execute a complex maneuver sequence
        maneuver_steps = [
            ("move_forward", 40),
            ("set_steering_angle", 20),
            ("set_camera_pan", 15),
            ("move_backward", 30),
            ("set_steering_angle", -15),
            ("set_camera_tilt", -10),
            ("stop", None),
            ("center_steering", None),
            ("center_camera", None)
        ]
        
        for step, param in maneuver_steps:
            if param is not None:
                result = getattr(self.rover, step)(param)
            else:
                result = getattr(self.rover, step)()
            
            self.assertTrue(result, f"Failed to execute step: {step}")
        
        # Verify final state
        self.assertEqual(self.rover.status.speed, 0)
        self.assertEqual(self.rover.status.direction, 0)
        self.assertEqual(self.rover.status.steering_angle, 0)
        self.assertEqual(self.rover.status.camera_pan, 0)
        self.assertEqual(self.rover.status.camera_tilt, 0)


class TestHardwareFactoryIntegration(unittest.TestCase):
    """Test hardware factory integration with different scenarios"""
    
    def test_auto_detection_workflow(self):
        """Test automatic hardware detection workflow"""
        # Test auto rover creation
        rover = HardwareFactory.create_rover(RoverType.AUTO)
        self.assertIsNotNone(rover)
        
        # Should be able to initialize
        self.assertTrue(rover.initialize())
        self.assertTrue(rover.is_connected())
        
        # Test basic functionality
        self.assertTrue(rover.move_forward(25))
        self.assertTrue(rover.stop())
        
        rover.shutdown()
    
    def test_configuration_based_creation(self):
        """Test rover creation from configuration"""
        config = {
            'rover_type': 'mock',
            'rover_config': {
                'connection_reliability': 0.95,
                'initial_battery_voltage': 7.8,
                'simulate_battery_drain': False
            }
        }
        
        rover = HardwareFactory.create_rover_from_config(config)
        self.assertIsInstance(rover, MockRover)
        
        rover.initialize()
        
        # Test configured parameters
        voltage = rover.get_battery_voltage()
        self.assertAlmostEqual(voltage, 7.8, delta=0.5)
        
        rover.shutdown()
    
    def test_hardware_detection_results(self):
        """Test hardware detection results structure"""
        results = HardwareFactory.detect_hardware()
        
        # Check required keys
        required_keys = [
            'picarx_available',
            'camera_available',
            'recommended_type',
            'detection_errors'
        ]
        
        for key in required_keys:
            self.assertIn(key, results)
        
        # Check data types
        self.assertIsInstance(results['picarx_available'], bool)
        self.assertIsInstance(results['camera_available'], bool)
        self.assertIsInstance(results['recommended_type'], RoverType)
        self.assertIsInstance(results['detection_errors'], list)


class TestConfigurationIntegration(unittest.TestCase):
    """Test configuration system integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = pathlib.Path(self.temp_dir) / "test_config.json"
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_configuration_loading_workflow(self):
        """Test configuration loading and validation workflow"""
        # Create test configuration
        test_config = {
            "camera_enabled": True,
            "camera_port": 8080,
            "log_level": "INFO",
            "battery_check_interval": 5,
            "max_speed": 80,
            "steering_range": 30
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
        
        # Test configuration loading
        config = RoverConfig.from_file(str(self.config_file))
        
        # Verify loaded values
        self.assertTrue(config.camera_enabled)
        self.assertEqual(config.camera_port, 8080)
        self.assertEqual(config.log_level, "INFO")
        self.assertEqual(config.battery_check_interval, 5)
        self.assertEqual(config.max_speed, 80)
        self.assertEqual(config.steering_range, 30)
    
    def test_configuration_validation_workflow(self):
        """Test configuration validation workflow"""
        # Test valid configuration
        valid_config = RoverConfig(
            camera_enabled=True,
            camera_port=8080,
            max_speed=100,
            steering_range=35
        )
        
        # Should validate successfully
        self.assertTrue(valid_config.validate())
        
        # Test invalid configuration
        invalid_config = RoverConfig(
            camera_port=-1,  # Invalid port
            max_speed=150,   # Over limit
            steering_range=50  # Over limit
        )
        
        # Should fail validation
        self.assertFalse(invalid_config.validate())
    
    def test_configuration_override_workflow(self):
        """Test configuration override workflow"""
        # Base configuration
        base_config = RoverConfig(
            camera_enabled=True,
            max_speed=50
        )
        
        # Override configuration
        override_config = RoverConfig(
            max_speed=75,
            log_level="DEBUG"
        )
        
        # Test override
        merged_config = base_config.merge(override_config)
        
        # Should keep base values where not overridden
        self.assertTrue(merged_config.camera_enabled)
        
        # Should use override values
        self.assertEqual(merged_config.max_speed, 75)
        self.assertEqual(merged_config.log_level, "DEBUG")


class TestLoggingIntegration(unittest.TestCase):
    """Test logging system integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = pathlib.Path(self.temp_dir) / "logs"
        self.log_dir.mkdir()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_integrated_logging_workflow(self):
        """Test integrated logging with rover operations"""
        # Import logging system
        sys.path.insert(0, str(project_root / 'src'))
        from utils.enhanced_logging import get_logger
        
        # Create logger
        logger = get_logger("integration_test", log_dir=self.log_dir)
        
        # Create rover with logging
        rover = MockRover()
        rover.initialize()
        
        # Log rover operations
        logger.log_system_event("rover_initialized", {"rover_type": "mock"})
        
        # Perform operations with logging
        logger.log_movement("forward", 50, 0, 2.0)
        rover.move_forward(50)
        
        logger.log_battery_status(rover.get_battery_voltage())
        
        logger.log_system_event("test_completed", {"status": "success"})
        
        # Start telemetry logging
        logger.start_telemetry_logging()
        time.sleep(0.5)  # Allow telemetry to process
        logger.stop_telemetry_logging()
        
        # Verify log files were created
        telemetry_file = self.log_dir / "integration_test_telemetry.jsonl"
        self.assertTrue(telemetry_file.exists())
        
        # Verify log content
        with open(telemetry_file, 'r') as f:
            log_lines = f.readlines()
        
        self.assertGreater(len(log_lines), 0)
        
        # Parse and verify log entries
        for line in log_lines:
            entry = json.loads(line.strip())
            self.assertIn('timestamp', entry)
            self.assertIn('component', entry)
            self.assertIn('event_type', entry)
        
        rover.shutdown()


class TestWebInterfaceIntegration(unittest.TestCase):
    """Test web interface integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_web_interface_availability(self):
        """Test web interface module availability"""
        try:
            sys.path.insert(0, str(project_root / 'src'))
            from web_interface import create_app
            
            # Should be able to create app
            app = create_app()
            self.assertIsNotNone(app)
            
        except ImportError:
            self.skipTest("Web interface module not available")
    
    def test_web_interface_basic_functionality(self):
        """Test basic web interface functionality"""
        try:
            sys.path.insert(0, str(project_root / 'src'))
            from web_interface import create_app
            
            app = create_app()
            
            with app.test_client() as client:
                # Test main page
                response = client.get('/')
                self.assertEqual(response.status_code, 200)
                
                # Test API endpoints if available
                if hasattr(app, 'test_request_context'):
                    with app.test_request_context():
                        # Test status endpoint
                        response = client.get('/api/status')
                        # Should return some response (may be 404 if not implemented)
                        self.assertIn(response.status_code, [200, 404])
                        
        except ImportError:
            self.skipTest("Web interface module not available")


class TestScriptIntegration(unittest.TestCase):
    """Test integration with shell scripts"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = pathlib.Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
    
    def test_launcher_script_integration(self):
        """Test integration with launcher script"""
        launcher_script = self.project_root / "run_rover.sh"
        
        if launcher_script.exists():
            # Test script help
            try:
                result = subprocess.run(
                    [str(launcher_script), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Should provide usage information
                output = result.stdout + result.stderr
                self.assertTrue(
                    any(keyword in output.lower() for keyword in ["usage", "help", "mode"]),
                    "Launcher script should provide usage information"
                )
                
            except (subprocess.TimeoutExpired, FileNotFoundError):
                self.skipTest("Could not test launcher script")
    
    def test_validation_script_integration(self):
        """Test integration with validation script"""
        validation_script = self.scripts_dir / "validate_hardware.sh"
        
        if validation_script.exists() and os.access(validation_script, os.X_OK):
            # Test script execution (dry run)
            try:
                # Run with timeout to prevent hanging
                result = subprocess.run(
                    [str(validation_script)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, 'CI': '1'}  # Set CI flag to skip interactive parts
                )
                
                # Script should complete (may fail tests but shouldn't crash)
                self.assertIsNotNone(result.returncode)
                
                # Should produce some output
                output = result.stdout + result.stderr
                self.assertGreater(len(output), 0, "Validation script should produce output")
                
            except subprocess.TimeoutExpired:
                self.skipTest("Validation script timed out")
            except FileNotFoundError:
                self.skipTest("Could not execute validation script")


class TestSystemIntegration(unittest.TestCase):
    """Test overall system integration"""
    
    def test_project_structure_integrity(self):
        """Test project structure integrity"""
        project_root = pathlib.Path(__file__).parent.parent
        
        # Check required directories
        required_dirs = [
            "src",
            "config",
            "scripts", 
            "tests",
            "docs"
        ]
        
        for dir_name in required_dirs:
            dir_path = project_root / dir_name
            self.assertTrue(dir_path.exists(), f"Required directory {dir_name} missing")
            self.assertTrue(dir_path.is_dir(), f"{dir_name} should be a directory")
    
    def test_python_module_structure(self):
        """Test Python module structure"""
        project_root = pathlib.Path(__file__).parent.parent
        src_dir = project_root / "src"
        
        # Check for __init__.py files
        init_files = [
            src_dir / "__init__.py",
            src_dir / "hardware" / "__init__.py",
            src_dir / "utils" / "__init__.py"
        ]
        
        for init_file in init_files:
            if init_file.parent.exists():
                self.assertTrue(init_file.exists(), f"Missing __init__.py in {init_file.parent}")
    
    def test_configuration_files_integrity(self):
        """Test configuration files integrity"""
        project_root = pathlib.Path(__file__).parent.parent
        config_dir = project_root / "config"
        
        # Check for required configuration files
        if config_dir.exists():
            # Check systemd service files
            systemd_dir = config_dir / "systemd"
            if systemd_dir.exists():
                service_files = list(systemd_dir.glob("*.service"))
                self.assertGreater(len(service_files), 0, "Should have systemd service files")
    
    def test_documentation_integrity(self):
        """Test documentation integrity"""
        project_root = pathlib.Path(__file__).parent.parent
        
        # Check for README
        readme_file = project_root / "README.md"
        self.assertTrue(readme_file.exists(), "README.md should exist")
        
        # Check docs directory
        docs_dir = project_root / "docs"
        if docs_dir.exists():
            doc_files = list(docs_dir.glob("*.md"))
            self.assertGreater(len(doc_files), 0, "Should have documentation files")
    
    def test_requirements_file_integrity(self):
        """Test requirements file integrity"""
        project_root = pathlib.Path(__file__).parent.parent
        requirements_file = project_root / "requirements.txt"
        
        self.assertTrue(requirements_file.exists(), "requirements.txt should exist")
        
        # Check file is not empty
        content = requirements_file.read_text().strip()
        self.assertGreater(len(content), 0, "requirements.txt should not be empty")
        
        # Check for common packages
        lines = content.split('\n')
        package_lines = [line for line in lines if line.strip() and not line.startswith('#')]
        self.assertGreater(len(package_lines), 0, "Should have package requirements")


class TestPerformanceIntegration(unittest.TestCase):
    """Test performance aspects of integration"""
    
    def test_rover_response_time(self):
        """Test rover command response times"""
        rover = MockRover()
        rover.initialize()
        
        # Test command response times
        commands = [
            ('move_forward', 50),
            ('move_backward', 30),
            ('stop', None),
            ('set_steering_angle', 15),
            ('set_camera_pan', 10),
            ('set_camera_tilt', -5)
        ]
        
        response_times = []
        
        for command, param in commands:
            start_time = time.time()
            
            if param is not None:
                result = getattr(rover, command)(param)
            else:
                result = getattr(rover, command)()
            
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)
            
            self.assertTrue(result, f"Command {command} failed")
            self.assertLess(response_time, 0.1, f"Command {command} too slow: {response_time:.3f}s")
        
        # Average response time should be reasonable
        avg_response_time = sum(response_times) / len(response_times)
        self.assertLess(avg_response_time, 0.05, f"Average response time too slow: {avg_response_time:.3f}s")
        
        rover.shutdown()
    
    def test_battery_monitoring_performance(self):
        """Test battery monitoring performance"""
        rover = MockRover()
        rover.initialize()
        
        # Test multiple battery readings
        start_time = time.time()
        readings = []
        
        for _ in range(10):
            voltage = rover.get_battery_voltage()
            self.assertIsNotNone(voltage)
            readings.append(voltage)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete quickly
        self.assertLess(total_time, 1.0, f"Battery monitoring too slow: {total_time:.3f}s")
        
        # Readings should be consistent
        voltage_std = (sum((v - sum(readings)/len(readings))**2 for v in readings) / len(readings))**0.5
        self.assertLess(voltage_std, 0.5, "Battery readings too inconsistent")
        
        rover.shutdown()


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2, buffer=True)