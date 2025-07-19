#!/usr/bin/env python3
"""
Test suite for Enhanced Logging System

Tests the functionality of the enhanced logging system including
structured logging, telemetry, alerts, and log rotation.
"""

import json
import os
import pathlib
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock
import sys

# Add src to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from utils.enhanced_logging import (
    RoverLogger, LogLevel, EventType, AlertConfig, 
    get_logger, start_all_telemetry, stop_all_telemetry
)


class TestEnhancedLogging(unittest.TestCase):
    """Test cases for enhanced logging system"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = pathlib.Path(self.temp_dir)
        
        # Create test logger
        self.logger = RoverLogger(
            component="test",
            log_dir=self.log_dir,
            alert_config=AlertConfig()
        )
        
    def tearDown(self):
        """Clean up test environment"""
        # Stop telemetry if running
        self.logger.stop_telemetry_logging()
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_logger_initialization(self):
        """Test logger initialization"""
        self.assertEqual(self.logger.component, "test")
        self.assertTrue(self.log_dir.exists())
        self.assertIsNotNone(self.logger.logger)
        
    def test_movement_logging(self):
        """Test movement logging functionality"""
        # Log a movement
        entry = self.logger.log_movement("forward", 50, 0, 2.5)
        
        # Check entry structure
        self.assertEqual(entry.event_type, EventType.MOVEMENT)
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.data['action'], "forward")
        self.assertEqual(entry.data['speed'], 50)
        self.assertEqual(entry.data['direction'], 0)
        self.assertEqual(entry.data['duration'], 2.5)
        
        # Check movement stats
        stats = self.logger.get_movement_stats()
        self.assertGreater(stats['total_runtime'], 0)
        self.assertGreater(stats['total_distance'], 0)
        self.assertIsNotNone(stats['last_movement'])
        
    def test_battery_logging_and_alerts(self):
        """Test battery logging and alert functionality"""
        # Mock alert callback
        alert_callback = MagicMock()
        self.logger.monitor.alert_callback = alert_callback
        
        # Test normal battery level
        entry = self.logger.log_battery_status(3.7, 75.0)
        self.assertEqual(entry.event_type, EventType.BATTERY)
        self.assertEqual(entry.level, LogLevel.INFO)
        
        # Test low battery alert
        self.logger.log_battery_status(3.2)
        alert_callback.assert_called_with(
            "battery_low", 
            "Low battery level: 3.2V", 
            {"voltage": 3.2}
        )
        
        # Test critical battery alert
        alert_callback.reset_mock()
        self.logger.log_battery_status(2.9)
        alert_callback.assert_called_with(
            "battery_critical", 
            "Critical battery level: 2.9V", 
            {"voltage": 2.9}
        )
        
    def test_system_event_logging(self):
        """Test system event logging"""
        data = {"version": "1.0.0", "startup_time": 5.2}
        entry = self.logger.log_system_event("startup", data, LogLevel.INFO)
        
        self.assertEqual(entry.event_type, EventType.SYSTEM)
        self.assertEqual(entry.level, LogLevel.INFO)
        self.assertEqual(entry.data, data)
        
    def test_error_logging(self):
        """Test error logging with exceptions"""
        test_exception = ValueError("Test error")
        entry = self.logger.log_error("Test error occurred", test_exception, {"context": "testing"})
        
        self.assertEqual(entry.event_type, EventType.ERROR)
        self.assertEqual(entry.level, LogLevel.ERROR)
        self.assertEqual(entry.data['exception_type'], "ValueError")
        self.assertEqual(entry.data['exception_message'], "Test error")
        self.assertEqual(entry.data['context'], "testing")
        
    def test_telemetry_logging(self):
        """Test telemetry logging to file"""
        # Start telemetry logging
        self.logger.start_telemetry_logging()
        
        # Log some events
        self.logger.log_movement("forward", 30, 0, 1.0)
        self.logger.log_battery_status(3.5)
        self.logger.log_system_event("test", {"data": "value"})
        
        # Wait for telemetry to process
        time.sleep(0.5)
        
        # Stop telemetry
        self.logger.stop_telemetry_logging()
        
        # Check telemetry file exists and has content
        telemetry_file = self.log_dir / "test_telemetry.jsonl"
        self.assertTrue(telemetry_file.exists())
        
        # Read and validate telemetry entries
        with open(telemetry_file, 'r') as f:
            lines = f.readlines()
            
        self.assertGreaterEqual(len(lines), 3)
        
        # Validate JSON structure
        for line in lines:
            entry = json.loads(line.strip())
            self.assertIn('timestamp', entry)
            self.assertIn('component', entry)
            self.assertIn('event_type', entry)
            self.assertIn('level', entry)
            self.assertIn('message', entry)
            self.assertIn('data', entry)
            
    def test_recent_logs_retrieval(self):
        """Test retrieval of recent log entries"""
        # Start telemetry to create log file
        self.logger.start_telemetry_logging()
        
        # Log some events
        self.logger.log_movement("forward", 30, 0)
        self.logger.log_battery_status(3.5)
        
        # Wait for processing
        time.sleep(0.5)
        self.logger.stop_telemetry_logging()
        
        # Get recent logs
        recent_logs = self.logger.get_recent_logs(minutes=1)
        self.assertGreaterEqual(len(recent_logs), 2)
        
        # Test filtering by event type
        movement_logs = self.logger.get_recent_logs(minutes=1, event_type=EventType.MOVEMENT)
        self.assertGreaterEqual(len(movement_logs), 1)
        self.assertEqual(movement_logs[0]['event_type'], 'movement')
        
    def test_alert_cooldown(self):
        """Test alert cooldown functionality"""
        alert_callback = MagicMock()
        self.logger.monitor.alert_callback = alert_callback
        
        # Set short cooldown for testing
        self.logger.monitor.alert_config.alert_cooldown = 1
        
        # Send first alert
        self.logger.log_battery_status(2.9)
        self.assertEqual(alert_callback.call_count, 1)
        
        # Send second alert immediately (should be blocked)
        self.logger.log_battery_status(2.8)
        self.assertEqual(alert_callback.call_count, 1)
        
        # Wait for cooldown and send third alert
        time.sleep(1.1)
        self.logger.log_battery_status(2.7)
        self.assertEqual(alert_callback.call_count, 2)
        
    def test_log_cleanup(self):
        """Test log cleanup functionality"""
        # Create some old log files
        old_log = self.log_dir / "old.log"
        old_log.write_text("old log content")
        
        # Set modification time to old
        old_time = time.time() - (8 * 24 * 60 * 60)  # 8 days ago
        os.utime(old_log, (old_time, old_time))
        
        # Create recent log file
        recent_log = self.log_dir / "recent.log"
        recent_log.write_text("recent log content")
        
        # Run cleanup
        self.logger.cleanup_old_logs(days_to_keep=7)
        
        # Check results
        self.assertFalse(old_log.exists())
        self.assertTrue(recent_log.exists())
        
    def test_global_logger_registry(self):
        """Test global logger registry functionality"""
        # Get logger instances
        logger1 = get_logger("component1", log_dir=self.log_dir)
        logger2 = get_logger("component1", log_dir=self.log_dir)  # Same component
        logger3 = get_logger("component2", log_dir=self.log_dir)  # Different component
        
        # Check that same component returns same instance
        self.assertIs(logger1, logger2)
        self.assertIsNot(logger1, logger3)
        
        # Test global telemetry control
        start_all_telemetry()
        self.assertTrue(logger1.running)
        self.assertTrue(logger3.running)
        
        stop_all_telemetry()
        self.assertFalse(logger1.running)
        self.assertFalse(logger3.running)


class TestLogRotationHandler(unittest.TestCase):
    """Test log rotation handler"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = pathlib.Path(self.temp_dir) / "test.log"
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
    def test_log_rotation(self):
        """Test that log rotation works correctly"""
        from utils.enhanced_logging import LogRotationHandler
        
        # Create handler with small max size for testing
        handler = LogRotationHandler(str(self.log_file), max_bytes=100, backup_count=2)
        
        # Create logger and add handler
        import logging
        logger = logging.getLogger("test_rotation")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Write enough data to trigger rotation
        for i in range(20):
            logger.info(f"This is test log message number {i} with some extra content to make it longer")
            
        # Check that backup files were created
        backup_files = list(pathlib.Path(self.temp_dir).glob("test.log.*"))
        self.assertGreater(len(backup_files), 0)
        
        handler.close()


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)