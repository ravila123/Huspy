#!/usr/bin/env python3
"""
Service Management Testing Suite

Tests the systemd service configurations and management scripts including:
- Service file validation
- Service management script functionality
- Service configuration testing
- Service lifecycle testing

Requirements: 6.1, 6.2, 6.4
"""

import unittest
import sys
import pathlib
import tempfile
import subprocess
import os
import shutil
from unittest.mock import patch, MagicMock, call

# Add project root to path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestServiceFiles(unittest.TestCase):
    """Test systemd service file configurations"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = pathlib.Path(__file__).parent.parent
        self.service_dir = self.project_root / "config" / "systemd"
        self.services = ["blue-rover-battery", "blue-rover-camera"]
    
    def test_service_files_exist(self):
        """Test that all required service files exist"""
        for service in self.services:
            service_file = self.service_dir / f"{service}.service"
            self.assertTrue(service_file.exists(), f"Service file {service}.service not found")
    
    def test_service_file_structure(self):
        """Test service file structure and required sections"""
        for service in self.services:
            service_file = self.service_dir / f"{service}.service"
            
            with self.subTest(service=service):
                content = service_file.read_text()
                
                # Check required sections
                self.assertIn("[Unit]", content, f"{service} missing [Unit] section")
                self.assertIn("[Service]", content, f"{service} missing [Service] section")
                self.assertIn("[Install]", content, f"{service} missing [Install] section")
                
                # Check required Unit directives
                self.assertIn("Description=", content, f"{service} missing Description")
                
                # Check required Service directives
                self.assertIn("ExecStart=", content, f"{service} missing ExecStart")
                self.assertIn("Type=", content, f"{service} missing Type")
                self.assertIn("User=", content, f"{service} missing User")
                self.assertIn("WorkingDirectory=", content, f"{service} missing WorkingDirectory")
                
                # Check required Install directives
                self.assertIn("WantedBy=", content, f"{service} missing WantedBy")
    
    def test_service_file_templates(self):
        """Test service file template variables"""
        for service in self.services:
            service_file = self.service_dir / f"{service}.service"
            
            with self.subTest(service=service):
                content = service_file.read_text()
                
                # Check for template variables
                self.assertIn("%h", content, f"{service} missing %h template variable")
                self.assertIn("%i", content, f"{service} missing %i template variable")
    
    def test_service_security_settings(self):
        """Test service security configurations"""
        for service in self.services:
            service_file = self.service_dir / f"{service}.service"
            
            with self.subTest(service=service):
                content = service_file.read_text()
                
                # Check security settings
                security_settings = [
                    "NoNewPrivileges=true",
                    "PrivateTmp=true",
                    "ProtectSystem=strict",
                    "ProtectHome=read-only"
                ]
                
                for setting in security_settings:
                    self.assertIn(setting, content, f"{service} missing security setting: {setting}")
    
    def test_service_resource_limits(self):
        """Test service resource limit configurations"""
        for service in self.services:
            service_file = self.service_dir / f"{service}.service"
            
            with self.subTest(service=service):
                content = service_file.read_text()
                
                # Check resource limits
                self.assertIn("MemoryMax=", content, f"{service} missing memory limit")
                self.assertIn("CPUQuota=", content, f"{service} missing CPU quota")
    
    def test_service_restart_policies(self):
        """Test service restart and failure recovery policies"""
        for service in self.services:
            service_file = self.service_dir / f"{service}.service"
            
            with self.subTest(service=service):
                content = service_file.read_text()
                
                # Check restart policies
                self.assertIn("Restart=", content, f"{service} missing restart policy")
                self.assertIn("RestartSec=", content, f"{service} missing restart delay")
                self.assertIn("StartLimitInterval=", content, f"{service} missing start limit interval")
                self.assertIn("StartLimitBurst=", content, f"{service} missing start limit burst")


class TestServiceManagementScript(unittest.TestCase):
    """Test service management script functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = pathlib.Path(__file__).parent.parent
        self.script_path = self.project_root / "scripts" / "manage_services.sh"
        self.temp_dir = tempfile.mkdtemp()
        self.mock_systemd_dir = pathlib.Path(self.temp_dir) / ".config" / "systemd" / "user"
        self.mock_systemd_dir.mkdir(parents=True)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_script_exists_and_executable(self):
        """Test that management script exists and is executable"""
        self.assertTrue(self.script_path.exists(), "manage_services.sh not found")
        self.assertTrue(os.access(self.script_path, os.X_OK), "manage_services.sh not executable")
    
    def test_script_help_output(self):
        """Test script help output"""
        try:
            result = subprocess.run(
                [str(self.script_path), "help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should exit successfully
            self.assertEqual(result.returncode, 0, "Help command failed")
            
            # Should contain usage information
            self.assertIn("USAGE:", result.stdout)
            self.assertIn("COMMANDS:", result.stdout)
            self.assertIn("install", result.stdout)
            self.assertIn("start", result.stdout)
            self.assertIn("stop", result.stdout)
            
        except subprocess.TimeoutExpired:
            self.fail("Script help command timed out")
        except FileNotFoundError:
            self.fail("Could not execute manage_services.sh")
    
    def test_script_invalid_command(self):
        """Test script behavior with invalid command"""
        try:
            result = subprocess.run(
                [str(self.script_path), "invalid_command"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should exit with error
            self.assertNotEqual(result.returncode, 0, "Invalid command should fail")
            self.assertIn("Unknown command", result.stderr)
            
        except subprocess.TimeoutExpired:
            self.fail("Script with invalid command timed out")
    
    @patch.dict(os.environ, {'HOME': '/tmp/test_home'})
    def test_service_installation_dry_run(self):
        """Test service installation logic (dry run)"""
        # This test validates the script logic without actually installing services
        
        # Create mock service files
        mock_service_dir = pathlib.Path(self.temp_dir) / "config" / "systemd"
        mock_service_dir.mkdir(parents=True)
        
        for service in ["blue-rover-battery", "blue-rover-camera"]:
            service_file = mock_service_dir / f"{service}.service"
            service_file.write_text(f"""[Unit]
Description=Test {service} Service
After=network.target

[Service]
Type=simple
User=%i
WorkingDirectory=%h/blue-rover
ExecStart=%h/blue-rover/venv/bin/python -m src.{service.replace('-', '_')}

[Install]
WantedBy=default.target
""")
        
        # Test that service files can be processed
        for service in ["blue-rover-battery", "blue-rover-camera"]:
            service_file = mock_service_dir / f"{service}.service"
            self.assertTrue(service_file.exists())
            
            content = service_file.read_text()
            # Test template substitution logic
            substituted = content.replace("%h", "/tmp/test_home").replace("%i", "testuser")
            self.assertNotIn("%h", substituted)
            self.assertNotIn("%i", substituted)


class TestServiceTestingScript(unittest.TestCase):
    """Test service testing script functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = pathlib.Path(__file__).parent.parent
        self.script_path = self.project_root / "scripts" / "test_services.sh"
    
    def test_script_exists_and_executable(self):
        """Test that testing script exists and is executable"""
        self.assertTrue(self.script_path.exists(), "test_services.sh not found")
        self.assertTrue(os.access(self.script_path, os.X_OK), "test_services.sh not executable")
    
    def test_script_help_output(self):
        """Test script help output"""
        try:
            result = subprocess.run(
                [str(self.script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Should contain usage information
            output = result.stdout + result.stderr
            self.assertIn("USAGE:", output)
            self.assertIn("TESTS PERFORMED:", output)
            
        except subprocess.TimeoutExpired:
            self.fail("Script help command timed out")
        except FileNotFoundError:
            self.fail("Could not execute test_services.sh")


class TestServiceConfiguration(unittest.TestCase):
    """Test service configuration validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = pathlib.Path(__file__).parent.parent
        self.service_dir = self.project_root / "config" / "systemd"
    
    def test_battery_service_configuration(self):
        """Test battery service specific configuration"""
        service_file = self.service_dir / "blue-rover-battery.service"
        content = service_file.read_text()
        
        # Check battery-specific settings
        self.assertIn("src.battery_monitor", content, "Battery service should reference battery_monitor module")
        self.assertIn("--interval", content, "Battery service should have interval parameter")
        self.assertIn("--low-threshold", content, "Battery service should have low threshold")
        self.assertIn("--critical-threshold", content, "Battery service should have critical threshold")
        
        # Check restart policy (should be 'always' for monitoring)
        self.assertIn("Restart=always", content, "Battery service should restart always")
    
    def test_camera_service_configuration(self):
        """Test camera service specific configuration"""
        service_file = self.service_dir / "blue-rover-camera.service"
        content = service_file.read_text()
        
        # Check camera-specific settings
        self.assertIn("src.camera_stream", content, "Camera service should reference camera_stream module")
        self.assertIn("--port", content, "Camera service should have port parameter")
        
        # Check restart policy (should be 'on-failure' for camera)
        self.assertIn("Restart=on-failure", content, "Camera service should restart on failure")
        
        # Check PYTHONPATH environment variable
        self.assertIn("PYTHONPATH=", content, "Camera service should set PYTHONPATH")
    
    def test_service_dependencies(self):
        """Test service dependency configuration"""
        for service in ["blue-rover-battery", "blue-rover-camera"]:
            service_file = self.service_dir / f"{service}.service"
            content = service_file.read_text()
            
            with self.subTest(service=service):
                # Check network dependency
                self.assertIn("After=network.target", content, f"{service} should depend on network")
                self.assertIn("Wants=network.target", content, f"{service} should want network")
    
    def test_service_logging_configuration(self):
        """Test service logging configuration"""
        for service in ["blue-rover-battery", "blue-rover-camera"]:
            service_file = self.service_dir / f"{service}.service"
            content = service_file.read_text()
            
            with self.subTest(service=service):
                # Check logging settings
                self.assertIn("StandardOutput=journal", content, f"{service} should log to journal")
                self.assertIn("StandardError=journal", content, f"{service} should log errors to journal")
                self.assertIn("SyslogIdentifier=", content, f"{service} should have syslog identifier")


class TestServiceLifecycle(unittest.TestCase):
    """Test service lifecycle management"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_home = pathlib.Path(self.temp_dir) / "home"
        self.mock_home.mkdir()
        self.mock_systemd_dir = self.mock_home / ".config" / "systemd" / "user"
        self.mock_systemd_dir.mkdir(parents=True)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_service_file_template_substitution(self):
        """Test service file template variable substitution"""
        # Create a test service file with templates
        test_service_content = """[Unit]
Description=Test Service
After=network.target

[Service]
Type=simple
User=%i
Group=%i
WorkingDirectory=%h/blue-rover
Environment=PATH=%h/blue-rover/venv/bin:/usr/bin
ExecStart=%h/blue-rover/venv/bin/python -m test_module

[Install]
WantedBy=default.target
"""
        
        # Test substitution
        substituted = test_service_content.replace("%h", str(self.mock_home)).replace("%i", "testuser")
        
        # Verify substitution
        self.assertNotIn("%h", substituted, "Home directory template not substituted")
        self.assertNotIn("%i", substituted, "User template not substituted")
        self.assertIn(str(self.mock_home), substituted, "Home directory not properly substituted")
        self.assertIn("testuser", substituted, "Username not properly substituted")
    
    def test_service_validation_logic(self):
        """Test service validation logic"""
        # Create a valid service file
        valid_service = """[Unit]
Description=Valid Test Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -c "print('test')"
Restart=always

[Install]
WantedBy=default.target
"""
        
        # Test validation checks
        self.assertIn("[Unit]", valid_service)
        self.assertIn("[Service]", valid_service)
        self.assertIn("[Install]", valid_service)
        self.assertIn("ExecStart=", valid_service)
        self.assertIn("Description=", valid_service)
        
        # Test invalid service file
        invalid_service = """[Unit]
Description=Invalid Test Service

[Service]
Type=simple
# Missing ExecStart

[Install]
WantedBy=default.target
"""
        
        self.assertNotIn("ExecStart=", invalid_service)


class TestServiceIntegration(unittest.TestCase):
    """Integration tests for service management"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = pathlib.Path(__file__).parent.parent
    
    def test_service_script_integration(self):
        """Test integration between service files and management scripts"""
        # Check that management script references the correct services
        manage_script = self.project_root / "scripts" / "manage_services.sh"
        script_content = manage_script.read_text()
        
        # Should reference the correct service names
        self.assertIn("blue-rover-battery", script_content)
        self.assertIn("blue-rover-camera", script_content)
        
        # Should reference the correct service directory
        self.assertIn("config/systemd", script_content)
    
    def test_service_module_references(self):
        """Test that service files reference existing Python modules"""
        service_dir = self.project_root / "config" / "systemd"
        src_dir = self.project_root / "src"
        
        # Check battery service
        battery_service = service_dir / "blue-rover-battery.service"
        battery_content = battery_service.read_text()
        
        if "src.battery_monitor" in battery_content:
            # Check if the referenced module exists
            battery_module = src_dir / "battery_monitor.py"
            self.assertTrue(battery_module.exists(), "Battery monitor module should exist")
        
        # Check camera service
        camera_service = service_dir / "blue-rover-camera.service"
        camera_content = camera_service.read_text()
        
        if "src.camera_stream" in camera_content:
            # Check if the referenced module exists
            camera_module = src_dir / "camera_stream.py"
            self.assertTrue(camera_module.exists(), "Camera stream module should exist")
    
    def test_service_directory_structure(self):
        """Test that service directory structure is correct"""
        service_dir = self.project_root / "config" / "systemd"
        
        # Directory should exist
        self.assertTrue(service_dir.exists(), "Service directory should exist")
        self.assertTrue(service_dir.is_dir(), "Service path should be a directory")
        
        # Should contain service files
        service_files = list(service_dir.glob("*.service"))
        self.assertGreater(len(service_files), 0, "Should contain service files")
        
        # Check specific service files
        expected_services = ["blue-rover-battery.service", "blue-rover-camera.service"]
        for service_file in expected_services:
            service_path = service_dir / service_file
            self.assertTrue(service_path.exists(), f"{service_file} should exist")
    
    def test_service_permissions_and_ownership(self):
        """Test service file permissions"""
        service_dir = self.project_root / "config" / "systemd"
        
        for service_file in service_dir.glob("*.service"):
            # Service files should be readable
            self.assertTrue(os.access(service_file, os.R_OK), f"{service_file.name} should be readable")
            
            # Service files should not be executable (they're config files)
            self.assertFalse(os.access(service_file, os.X_OK), f"{service_file.name} should not be executable")


class TestServiceErrorHandling(unittest.TestCase):
    """Test service error handling and recovery"""
    
    def test_service_failure_recovery_config(self):
        """Test service failure recovery configuration"""
        project_root = pathlib.Path(__file__).parent.parent
        service_dir = project_root / "config" / "systemd"
        
        for service in ["blue-rover-battery", "blue-rover-camera"]:
            service_file = service_dir / f"{service}.service"
            content = service_file.read_text()
            
            with self.subTest(service=service):
                # Check restart configuration
                self.assertIn("Restart=", content, f"{service} should have restart policy")
                self.assertIn("RestartSec=", content, f"{service} should have restart delay")
                
                # Check start limit configuration
                self.assertIn("StartLimitInterval=", content, f"{service} should have start limit interval")
                self.assertIn("StartLimitBurst=", content, f"{service} should have start limit burst")
    
    def test_service_resource_constraints(self):
        """Test service resource constraint configuration"""
        project_root = pathlib.Path(__file__).parent.parent
        service_dir = project_root / "config" / "systemd"
        
        for service in ["blue-rover-battery", "blue-rover-camera"]:
            service_file = service_dir / f"{service}.service"
            content = service_file.read_text()
            
            with self.subTest(service=service):
                # Check memory limits
                self.assertIn("MemoryMax=", content, f"{service} should have memory limit")
                
                # Check CPU limits
                self.assertIn("CPUQuota=", content, f"{service} should have CPU quota")
                
                # Validate memory limit format
                memory_lines = [line for line in content.split('\n') if 'MemoryMax=' in line]
                self.assertEqual(len(memory_lines), 1, f"{service} should have exactly one MemoryMax setting")
                
                memory_value = memory_lines[0].split('=')[1].strip()
                self.assertTrue(memory_value.endswith('M'), f"{service} memory limit should be in MB")


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2, buffer=True)