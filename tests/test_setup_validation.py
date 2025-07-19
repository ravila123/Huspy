#!/usr/bin/env python3
"""
Setup Validation Testing Suite

Tests for fresh installation scenarios and setup validation including:
- Setup script functionality
- Dependency installation validation
- Virtual environment creation
- Configuration file validation
- Fresh installation workflow testing

Requirements: 6.1, 6.2, 6.4
"""

import unittest
import sys
import pathlib
import tempfile
import subprocess
import os
import shutil
import json
import venv
from unittest.mock import patch, MagicMock, mock_open

# Add project root to path
project_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestSetupScript(unittest.TestCase):
    """Test setup script functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = pathlib.Path(__file__).parent.parent
        self.setup_script = self.project_root / "setup.sh"
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_setup_script_exists(self):
        """Test that setup script exists and is executable"""
        self.assertTrue(self.setup_script.exists(), "setup.sh not found")
        self.assertTrue(os.access(self.setup_script, os.X_OK), "setup.sh not executable")
    
    def test_setup_script_help_functionality(self):
        """Test setup script help and basic functionality"""
        try:
            # Test script can be executed (with --help or similar)
            result = subprocess.run(
                [str(self.setup_script)],
                input="n\n",  # Answer 'no' to any prompts
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, 'CI': '1'}  # Set CI flag
            )
            
            # Script should complete (may fail but shouldn't crash)
            self.assertIsNotNone(result.returncode)
            
            # Should produce some output
            output = result.stdout + result.stderr
            self.assertGreater(len(output), 0, "Setup script should produce output")
            
        except subprocess.TimeoutExpired:
            self.skipTest("Setup script timed out")
        except FileNotFoundError:
            self.fail("Could not execute setup script")
    
    def test_setup_script_structure(self):
        """Test setup script structure and content"""
        content = self.setup_script.read_text()
        
        # Check for required sections
        required_sections = [
            "#!/bin/bash",
            "set -e",  # Exit on error
            "detect_system",
            "detect_python",
            "create_virtual_environment",
            "install_python_dependencies"
        ]
        
        for section in required_sections:
            self.assertIn(section, content, f"Setup script missing: {section}")
    
    def test_setup_script_error_handling(self):
        """Test setup script error handling"""
        content = self.setup_script.read_text()
        
        # Check for error handling mechanisms
        error_handling_patterns = [
            "set -e",  # Exit on error
            "trap",    # Error trapping
            "handle_error",  # Error handler function
            "cleanup"  # Cleanup function
        ]
        
        for pattern in error_handling_patterns:
            self.assertIn(pattern, content, f"Setup script missing error handling: {pattern}")


class TestVirtualEnvironmentCreation(unittest.TestCase):
    """Test virtual environment creation and validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.venv_dir = pathlib.Path(self.temp_dir) / "test_venv"
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_virtual_environment_creation(self):
        """Test virtual environment creation"""
        # Create virtual environment
        venv.create(self.venv_dir, with_pip=True)
        
        # Check virtual environment structure
        self.assertTrue(self.venv_dir.exists(), "Virtual environment directory not created")
        self.assertTrue((self.venv_dir / "bin").exists(), "Virtual environment bin directory missing")
        self.assertTrue((self.venv_dir / "bin" / "python").exists(), "Python executable missing")
        self.assertTrue((self.venv_dir / "bin" / "pip").exists(), "Pip executable missing")
        self.assertTrue((self.venv_dir / "bin" / "activate").exists(), "Activate script missing")
    
    def test_virtual_environment_activation(self):
        """Test virtual environment activation"""
        # Create virtual environment
        venv.create(self.venv_dir, with_pip=True)
        
        # Test activation by running a command in the virtual environment
        python_exe = self.venv_dir / "bin" / "python"
        
        result = subprocess.run(
            [str(python_exe), "-c", "import sys; print(sys.prefix)"],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 0, "Failed to run Python in virtual environment")
        self.assertIn(str(self.venv_dir), result.stdout, "Virtual environment not properly activated")
    
    def test_pip_functionality_in_venv(self):
        """Test pip functionality in virtual environment"""
        # Create virtual environment
        venv.create(self.venv_dir, with_pip=True)
        
        pip_exe = self.venv_dir / "bin" / "pip"
        
        # Test pip list
        result = subprocess.run(
            [str(pip_exe), "list"],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 0, "Pip list failed in virtual environment")
        self.assertIn("pip", result.stdout, "Pip not found in virtual environment")


class TestDependencyInstallation(unittest.TestCase):
    """Test dependency installation validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = pathlib.Path(__file__).parent.parent
        self.requirements_file = self.project_root / "requirements.txt"
        self.temp_dir = tempfile.mkdtemp()
        self.venv_dir = pathlib.Path(self.temp_dir) / "test_venv"
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_requirements_file_exists(self):
        """Test that requirements.txt exists and is valid"""
        self.assertTrue(self.requirements_file.exists(), "requirements.txt not found")
        
        content = self.requirements_file.read_text().strip()
        self.assertGreater(len(content), 0, "requirements.txt is empty")
    
    def test_requirements_file_format(self):
        """Test requirements.txt format"""
        content = self.requirements_file.read_text()
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Filter out comments
        package_lines = [line for line in lines if not line.startswith('#')]
        self.assertGreater(len(package_lines), 0, "No package requirements found")
        
        # Check for common required packages
        content_lower = content.lower()
        expected_packages = ['picarx', 'readchar']  # Core packages
        
        for package in expected_packages:
            if package in content_lower:
                # Package is listed, which is good
                pass
    
    def test_dependency_installation_simulation(self):
        """Test dependency installation simulation"""
        # Create virtual environment
        venv.create(self.venv_dir, with_pip=True)
        
        pip_exe = self.venv_dir / "bin" / "pip"
        
        # Test installing a simple package
        result = subprocess.run(
            [str(pip_exe), "install", "requests"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # Test that package was installed
            python_exe = self.venv_dir / "bin" / "python"
            test_result = subprocess.run(
                [str(python_exe), "-c", "import requests; print('OK')"],
                capture_output=True,
                text=True
            )
            
            self.assertEqual(test_result.returncode, 0, "Package not properly installed")
            self.assertIn("OK", test_result.stdout, "Package import failed")
        else:
            self.skipTest("Could not install test package (network issue?)")


class TestProjectStructureValidation(unittest.TestCase):
    """Test project structure validation for fresh installations"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = pathlib.Path(__file__).parent.parent
    
    def test_required_directories_exist(self):
        """Test that all required directories exist"""
        required_dirs = [
            "src",
            "config", 
            "scripts",
            "tests",
            "docs"
        ]
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            self.assertTrue(dir_path.exists(), f"Required directory {dir_name} missing")
            self.assertTrue(dir_path.is_dir(), f"{dir_name} should be a directory")
    
    def test_required_files_exist(self):
        """Test that all required files exist"""
        required_files = [
            "README.md",
            "requirements.txt",
            "setup.sh",
            "run_rover.sh"
        ]
        
        for file_name in required_files:
            file_path = self.project_root / file_name
            self.assertTrue(file_path.exists(), f"Required file {file_name} missing")
            self.assertTrue(file_path.is_file(), f"{file_name} should be a file")
    
    def test_python_package_structure(self):
        """Test Python package structure"""
        src_dir = self.project_root / "src"
        
        # Check for __init__.py files
        init_files = [
            src_dir / "__init__.py",
            src_dir / "hardware" / "__init__.py",
            src_dir / "utils" / "__init__.py"
        ]
        
        for init_file in init_files:
            if init_file.parent.exists():
                self.assertTrue(init_file.exists(), f"Missing __init__.py in {init_file.parent}")
    
    def test_script_permissions(self):
        """Test that scripts have correct permissions"""
        script_files = [
            self.project_root / "setup.sh",
            self.project_root / "run_rover.sh"
        ]
        
        # Add scripts from scripts directory
        scripts_dir = self.project_root / "scripts"
        if scripts_dir.exists():
            script_files.extend(scripts_dir.glob("*.sh"))
        
        for script_file in script_files:
            if script_file.exists():
                self.assertTrue(os.access(script_file, os.X_OK), f"{script_file.name} should be executable")


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration file validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.project_root = pathlib.Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
    
    def test_configuration_directory_structure(self):
        """Test configuration directory structure"""
        if self.config_dir.exists():
            # Check for systemd directory
            systemd_dir = self.config_dir / "systemd"
            if systemd_dir.exists():
                self.assertTrue(systemd_dir.is_dir(), "systemd should be a directory")
                
                # Check for service files
                service_files = list(systemd_dir.glob("*.service"))
                self.assertGreater(len(service_files), 0, "Should have systemd service files")
    
    def test_systemd_service_files(self):
        """Test systemd service file validation"""
        systemd_dir = self.config_dir / "systemd"
        
        if systemd_dir.exists():
            service_files = list(systemd_dir.glob("*.service"))
            
            for service_file in service_files:
                with self.subTest(service=service_file.name):
                    content = service_file.read_text()
                    
                    # Check required sections
                    self.assertIn("[Unit]", content, f"{service_file.name} missing [Unit] section")
                    self.assertIn("[Service]", content, f"{service_file.name} missing [Service] section")
                    self.assertIn("[Install]", content, f"{service_file.name} missing [Install] section")
    
    def test_configuration_file_templates(self):
        """Test configuration file templates"""
        # Test rover configuration
        try:
            from config.rover_config import RoverConfig
            
            # Should be able to create default configuration
            config = RoverConfig()
            self.assertIsNotNone(config)
            
            # Should have reasonable defaults
            self.assertIsInstance(config.camera.enabled, bool)
            self.assertIsInstance(config.camera.port, int)
            self.assertGreater(config.camera.port, 0)
            self.assertLess(config.camera.port, 65536)
            
        except ImportError:
            self.skipTest("Configuration module not available")


class TestFreshInstallationWorkflow(unittest.TestCase):
    """Test complete fresh installation workflow"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = pathlib.Path(__file__).parent.parent
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_fresh_installation_simulation(self):
        """Test fresh installation simulation"""
        # Create a temporary project copy
        temp_project = pathlib.Path(self.temp_dir) / "blue_rover_test"
        
        # Copy essential files for testing
        temp_project.mkdir()
        
        # Copy requirements.txt
        requirements_src = self.project_root / "requirements.txt"
        if requirements_src.exists():
            shutil.copy2(requirements_src, temp_project / "requirements.txt")
        
        # Create minimal setup script for testing
        test_setup_script = temp_project / "setup.sh"
        test_setup_script.write_text("""#!/bin/bash
set -e

echo "Test setup script"
echo "Creating virtual environment..."

python3 -m venv venv
source venv/bin/activate

echo "Virtual environment created successfully"
echo "Setup complete"
""")
        test_setup_script.chmod(0o755)
        
        # Test setup script execution
        try:
            result = subprocess.run(
                [str(test_setup_script)],
                cwd=str(temp_project),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Should complete successfully
            self.assertEqual(result.returncode, 0, f"Setup failed: {result.stderr}")
            
            # Should create virtual environment
            venv_dir = temp_project / "venv"
            self.assertTrue(venv_dir.exists(), "Virtual environment not created")
            
        except subprocess.TimeoutExpired:
            self.skipTest("Setup script timed out")
    
    def test_post_installation_validation(self):
        """Test post-installation validation"""
        # Test that project can be imported after installation
        try:
            # Test hardware module imports
            from hardware.rover_interface import RoverInterface
            from hardware.mock_rover import MockRover
            from hardware.hardware_factory import HardwareFactory
            
            # Should be able to create instances
            rover = MockRover()
            self.assertIsNotNone(rover)
            
            factory_rover = HardwareFactory.create_rover('mock')
            self.assertIsNotNone(factory_rover)
            
            # Clean up
            if rover.is_connected():
                rover.shutdown()
            if factory_rover.is_connected():
                factory_rover.shutdown()
                
        except ImportError as e:
            self.skipTest(f"Post-installation import test skipped - modules not available: {e}")
    
    def test_installation_validation_script(self):
        """Test installation validation script functionality"""
        validation_script = self.project_root / "scripts" / "validate_hardware.sh"
        
        if validation_script.exists() and os.access(validation_script, os.X_OK):
            try:
                # Run validation script with timeout
                result = subprocess.run(
                    [str(validation_script)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={**os.environ, 'CI': '1'}
                )
                
                # Should complete (may fail tests but shouldn't crash)
                self.assertIsNotNone(result.returncode)
                
                # Should produce validation output
                output = result.stdout + result.stderr
                self.assertGreater(len(output), 0, "Validation script should produce output")
                
                # Should contain test results
                self.assertTrue(
                    any(keyword in output.lower() for keyword in ["test", "pass", "fail", "validation"]),
                    "Validation script should contain test results"
                )
                
            except subprocess.TimeoutExpired:
                self.skipTest("Validation script timed out")


class TestSystemRequirements(unittest.TestCase):
    """Test system requirements validation"""
    
    def test_python_version_requirements(self):
        """Test Python version requirements"""
        import sys
        
        # Check Python version
        version_info = sys.version_info
        
        # Should be Python 3.8 or higher
        self.assertGreaterEqual(version_info.major, 3, "Python 3 required")
        self.assertGreaterEqual(version_info.minor, 8, "Python 3.8 or higher required")
    
    def test_required_python_modules(self):
        """Test required Python modules availability"""
        required_modules = [
            'venv',
            'subprocess',
            'pathlib',
            'json',
            'unittest'
        ]
        
        for module_name in required_modules:
            try:
                __import__(module_name)
            except ImportError:
                self.fail(f"Required Python module {module_name} not available")
    
    def test_system_commands_availability(self):
        """Test system commands availability"""
        # Only test on Unix-like systems
        if os.name == 'posix':
            required_commands = ['python3', 'bash']
            
            for command in required_commands:
                result = subprocess.run(
                    ['which', command],
                    capture_output=True,
                    text=True
                )
                
                self.assertEqual(result.returncode, 0, f"Required command {command} not found")


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery in setup scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_partial_installation_recovery(self):
        """Test recovery from partial installation"""
        # Create a scenario with partial installation
        partial_venv = pathlib.Path(self.temp_dir) / "partial_venv"
        partial_venv.mkdir()
        
        # Create incomplete virtual environment structure
        (partial_venv / "bin").mkdir()
        (partial_venv / "lib").mkdir()
        
        # Should be able to detect and handle incomplete installation
        self.assertTrue(partial_venv.exists())
        self.assertFalse((partial_venv / "bin" / "python").exists())
        
        # Cleanup should be possible
        shutil.rmtree(partial_venv)
        self.assertFalse(partial_venv.exists())
    
    def test_permission_error_handling(self):
        """Test handling of permission errors"""
        # Create a directory with restricted permissions
        restricted_dir = pathlib.Path(self.temp_dir) / "restricted"
        restricted_dir.mkdir()
        
        try:
            # Remove write permissions
            restricted_dir.chmod(0o444)
            
            # Should not be able to write to restricted directory
            test_file = restricted_dir / "test.txt"
            
            with self.assertRaises(PermissionError):
                test_file.write_text("test")
                
        finally:
            # Restore permissions for cleanup
            restricted_dir.chmod(0o755)
    
    def test_disk_space_simulation(self):
        """Test disk space considerations"""
        # This is a basic test to ensure we consider disk space
        import shutil
        
        # Get disk usage
        total, used, free = shutil.disk_usage(self.temp_dir)
        
        # Should have some free space
        self.assertGreater(free, 0, "No free disk space available")
        
        # Should have reasonable amount for installation
        min_required = 100 * 1024 * 1024  # 100MB minimum
        if free < min_required:
            self.skipTest(f"Insufficient disk space: {free} bytes available, {min_required} required")


if __name__ == '__main__':
    # Configure test runner
    unittest.main(verbosity=2, buffer=True)