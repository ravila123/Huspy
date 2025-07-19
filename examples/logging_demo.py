#!/usr/bin/env python3
"""
Enhanced Logging System Demo

Demonstrates the capabilities of the Blue Rover enhanced logging system
including structured logging, telemetry, alerts, and real-time monitoring.
"""

import sys
import time
import pathlib
import random
from datetime import datetime

# Add src to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / 'src'))

from utils.enhanced_logging import get_logger, start_all_telemetry, stop_all_telemetry


def demo_movement_logging(logger):
    """Demonstrate movement logging"""
    print("=== Movement Logging Demo ===")
    
    movements = [
        ("forward", 50, 0, 2.0),
        ("backward", 30, 0, 1.5),
        ("turn_left", 40, -25, 1.0),
        ("turn_right", 40, 25, 1.0),
        ("stop", 0, 0, 0.5)
    ]
    
    for action, speed, direction, duration in movements:
        logger.log_movement(action, speed, direction, duration)
        print(f"Logged movement: {action} (speed={speed}, direction={direction}, duration={duration}s)")
        time.sleep(0.5)
        
    # Show movement statistics
    stats = logger.get_movement_stats()
    print(f"Movement Stats: {stats}")
    print()


def demo_battery_monitoring(logger):
    """Demonstrate battery monitoring and alerts"""
    print("=== Battery Monitoring Demo ===")
    
    # Simulate battery discharge
    voltages = [4.1, 3.8, 3.5, 3.3, 3.1, 2.9, 2.7]
    
    for voltage in voltages:
        percentage = max(0, min(100, (voltage - 3.0) / 1.2 * 100))
        logger.log_battery_status(voltage, percentage)
        print(f"Battery: {voltage}V ({percentage:.1f}%)")
        time.sleep(0.3)
    
    print()


def demo_system_events(logger):
    """Demonstrate system event logging"""
    print("=== System Events Demo ===")
    
    events = [
        ("startup", {"version": "1.2.3", "boot_time": 15.2}),
        ("wifi_connected", {"ssid": "RoverNet", "signal_strength": -42}),
        ("camera_initialized", {"resolution": "1080p", "fps": 30}),
        ("controller_paired", {"type": "PS5", "battery": 85}),
        ("service_started", {"service": "battery_monitor", "pid": 1234})
    ]
    
    for event, data in events:
        logger.log_system_event(event, data)
        print(f"System event: {event} - {data}")
        time.sleep(0.2)
    
    print()


def demo_camera_events(logger):
    """Demonstrate camera event logging"""
    print("=== Camera Events Demo ===")
    
    logger.log_camera_event("stream_started", {"resolution": "720p", "fps": 30, "bitrate": 2000})
    logger.log_camera_event("position_changed", {"pan": 45, "tilt": -10})
    logger.log_camera_event("recording_started", {"filename": "rover_session_001.mp4"})
    logger.log_camera_event("recording_stopped", {"duration": 120.5, "file_size": "45MB"})
    
    print("Camera events logged")
    print()


def demo_controller_events(logger):
    """Demonstrate controller event logging"""
    print("=== Controller Events Demo ===")
    
    logger.log_controller_event("connected", {"type": "PS5", "battery": 75})
    logger.log_controller_event("button_pressed", {"button": "X", "timestamp": time.time()})
    logger.log_controller_event("stick_moved", {"stick": "left", "x": 0.8, "y": -0.3})
    logger.log_controller_event("disconnected", {"reason": "low_battery", "session_duration": 1800})
    
    print("Controller events logged")
    print()


def demo_error_handling(logger):
    """Demonstrate error logging"""
    print("=== Error Handling Demo ===")
    
    # Log various types of errors
    logger.log_error("Hardware connection failed", ConnectionError("PicarX not responding"))
    logger.log_error("Camera initialization failed", RuntimeError("Camera module not found"))
    logger.log_error("Configuration error", ValueError("Invalid speed value: -150"))
    
    print("Error events logged")
    print()


def demo_network_events(logger):
    """Demonstrate network event logging"""
    print("=== Network Events Demo ===")
    
    logger.log_network_event("ssh_connection", {"client_ip": "192.168.1.100", "user": "pi"})
    logger.log_network_event("web_request", {"endpoint": "/camera/stream", "method": "GET"})
    logger.log_network_event("mqtt_message", {"topic": "rover/status", "payload_size": 256})
    logger.log_network_event("connection_lost", {"interface": "wlan0", "duration": 5.2})
    
    print("Network events logged")
    print()


def demo_telemetry_retrieval(logger):
    """Demonstrate telemetry data retrieval"""
    print("=== Telemetry Retrieval Demo ===")
    
    # Get recent logs
    recent_logs = logger.get_recent_logs(minutes=5)
    print(f"Recent logs (last 5 minutes): {len(recent_logs)} entries")
    
    if recent_logs:
        print("Sample recent entries:")
        for i, entry in enumerate(recent_logs[:3]):
            timestamp = datetime.fromtimestamp(entry['timestamp'])
            print(f"  {i+1}. [{timestamp.strftime('%H:%M:%S')}] {entry['component']} | {entry['event_type']} | {entry['message']}")
    
    # Get movement-specific logs
    from utils.enhanced_logging import EventType
    movement_logs = logger.get_recent_logs(minutes=5, event_type=EventType.MOVEMENT)
    print(f"Movement logs: {len(movement_logs)} entries")
    
    print()


def custom_alert_handler(alert_type, message, data):
    """Custom alert handler for demonstration"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🚨 CUSTOM ALERT [{alert_type}] {timestamp}")
    print(f"   Message: {message}")
    print(f"   Data: {data}")
    print()


def main():
    """Main demonstration function"""
    print("Blue Rover Enhanced Logging System Demo")
    print("=" * 50)
    print()
    
    # Create logger with custom alert handler
    logger = get_logger("demo", alert_callback=custom_alert_handler)
    
    # Start telemetry logging
    print("Starting telemetry logging...")
    start_all_telemetry()
    
    try:
        # Run demonstrations
        demo_movement_logging(logger)
        demo_battery_monitoring(logger)
        demo_system_events(logger)
        demo_camera_events(logger)
        demo_controller_events(logger)
        demo_error_handling(logger)
        demo_network_events(logger)
        
        # Wait for telemetry to process
        print("Waiting for telemetry processing...")
        time.sleep(2)
        
        # Demonstrate telemetry retrieval
        demo_telemetry_retrieval(logger)
        
        # Show final statistics
        print("=== Final Statistics ===")
        stats = logger.get_movement_stats()
        print(f"Total movement time: {stats['total_runtime']:.1f}s")
        print(f"Estimated distance: {stats['total_distance']:.1f} units")
        
        # Show log files created
        log_dir = pathlib.Path("logs")
        if log_dir.exists():
            log_files = list(log_dir.glob("demo*"))
            print(f"Log files created: {len(log_files)}")
            for log_file in log_files:
                size = log_file.stat().st_size
                print(f"  - {log_file.name} ({size} bytes)")
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    
    finally:
        # Stop telemetry logging
        print("\nStopping telemetry logging...")
        stop_all_telemetry()
        
    print("\nDemo completed!")


if __name__ == "__main__":
    main()