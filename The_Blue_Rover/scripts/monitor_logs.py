#!/usr/bin/env python3
"""
Real-time Log Monitor for Blue Rover

Monitors log files in real-time and provides alerts for critical events.
Can be used for debugging, monitoring, and alerting.
"""

import argparse
import json
import os
import pathlib
import select
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class LogEventHandler(FileSystemEventHandler):
    """Handle file system events for log files"""
    
    def __init__(self, monitor):
        self.monitor = monitor
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(('.log', '.jsonl')):
            self.monitor.handle_file_change(event.src_path)


class AlertManager:
    """Manage alerts and notifications"""
    
    def __init__(self):
        self.alert_counts: Dict[str, int] = {}
        self.last_alert_time: Dict[str, float] = {}
        self.alert_cooldown = 60  # seconds
        
    def should_alert(self, alert_type: str) -> bool:
        """Check if we should send an alert based on cooldown"""
        now = time.time()
        last_time = self.last_alert_time.get(alert_type, 0)
        
        if now - last_time >= self.alert_cooldown:
            self.last_alert_time[alert_type] = now
            self.alert_counts[alert_type] = self.alert_counts.get(alert_type, 0) + 1
            return True
        return False
        
    def send_alert(self, alert_type: str, message: str, data: Optional[Dict] = None):
        """Send an alert (can be extended for email, SMS, etc.)"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert_msg = f"🚨 ALERT [{alert_type}] {timestamp}: {message}"
        
        if data:
            alert_msg += f" | Data: {json.dumps(data, indent=2)}"
            
        print(alert_msg)
        
        # Could extend this to send emails, push notifications, etc.
        # For now, just print to console and could log to a special alert file
        
    def get_alert_stats(self) -> Dict[str, int]:
        """Get alert statistics"""
        return self.alert_counts.copy()


class LogMonitor:
    """Real-time log monitoring system"""
    
    def __init__(self, log_dir: pathlib.Path, alert_manager: AlertManager):
        self.log_dir = log_dir
        self.alert_manager = alert_manager
        self.observer = Observer()
        self.running = False
        self.file_positions: Dict[str, int] = {}
        
        # Alert thresholds
        self.error_threshold = 5  # errors per minute
        self.battery_critical = 3.0  # volts
        self.battery_low = 3.3  # volts
        
        # Tracking
        self.error_count = 0
        self.error_window_start = time.time()
        self.last_battery_voltage = None
        
    def start(self):
        """Start monitoring"""
        if not self.log_dir.exists():
            print(f"Log directory {self.log_dir} does not exist")
            return
            
        print(f"Starting log monitor for: {self.log_dir}")
        
        # Set up file system watcher
        event_handler = LogEventHandler(self)
        self.observer.schedule(event_handler, str(self.log_dir), recursive=True)
        self.observer.start()
        
        # Initialize file positions for existing files
        self._initialize_file_positions()
        
        self.running = True
        print("Log monitor started. Press Ctrl+C to stop.")
        
    def stop(self):
        """Stop monitoring"""
        self.running = False
        self.observer.stop()
        self.observer.join()
        print("Log monitor stopped.")
        
    def _initialize_file_positions(self):
        """Initialize file positions to end of existing files"""
        for log_file in self.log_dir.glob("*.log"):
            if log_file.is_file():
                self.file_positions[str(log_file)] = log_file.stat().st_size
                
        for telemetry_file in self.log_dir.glob("*_telemetry.jsonl"):
            if telemetry_file.is_file():
                self.file_positions[str(telemetry_file)] = telemetry_file.stat().st_size
                
    def handle_file_change(self, file_path: str):
        """Handle changes to log files"""
        try:
            if file_path.endswith('.jsonl'):
                self._process_telemetry_file(file_path)
            elif file_path.endswith('.log'):
                self._process_log_file(file_path)
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            
    def _process_telemetry_file(self, file_path: str):
        """Process telemetry JSON lines file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Seek to last known position
                last_pos = self.file_positions.get(file_path, 0)
                f.seek(last_pos)
                
                # Read new lines
                new_lines = f.readlines()
                
                # Update position
                self.file_positions[file_path] = f.tell()
                
                # Process each new line
                for line in new_lines:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            self._analyze_telemetry_entry(entry)
                        except json.JSONDecodeError as e:
                            print(f"Invalid JSON in telemetry: {e}")
                            
        except Exception as e:
            print(f"Error reading telemetry file {file_path}: {e}")
            
    def _process_log_file(self, file_path: str):
        """Process standard log file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Seek to last known position
                last_pos = self.file_positions.get(file_path, 0)
                f.seek(last_pos)
                
                # Read new lines
                new_lines = f.readlines()
                
                # Update position
                self.file_positions[file_path] = f.tell()
                
                # Process each new line
                for line in new_lines:
                    line = line.strip()
                    if line:
                        self._analyze_log_line(line, file_path)
                        
        except Exception as e:
            print(f"Error reading log file {file_path}: {e}")
            
    def _analyze_telemetry_entry(self, entry: Dict):
        """Analyze telemetry entry for alerts"""
        event_type = entry.get('event_type', '')
        level = entry.get('level', '')
        data = entry.get('data', {})
        
        # Check for battery alerts
        if event_type == 'battery':
            voltage = data.get('voltage', 0)
            self.last_battery_voltage = voltage
            
            if voltage <= self.battery_critical:
                if self.alert_manager.should_alert('battery_critical'):
                    self.alert_manager.send_alert(
                        'battery_critical',
                        f'Critical battery level: {voltage}V',
                        {'voltage': voltage, 'component': entry.get('component')}
                    )
            elif voltage <= self.battery_low:
                if self.alert_manager.should_alert('battery_low'):
                    self.alert_manager.send_alert(
                        'battery_low',
                        f'Low battery level: {voltage}V',
                        {'voltage': voltage, 'component': entry.get('component')}
                    )
                    
        # Check for error events
        if level == 'ERROR' or event_type == 'error':
            self._track_error_rate()
            
            # Send immediate alert for critical errors
            if 'critical' in entry.get('message', '').lower():
                if self.alert_manager.should_alert('critical_error'):
                    self.alert_manager.send_alert(
                        'critical_error',
                        f"Critical error: {entry.get('message', 'Unknown')}",
                        entry
                    )
                    
        # Check for system events
        if event_type == 'system':
            message = entry.get('message', '').lower()
            if 'shutdown' in message or 'crash' in message:
                if self.alert_manager.should_alert('system_event'):
                    self.alert_manager.send_alert(
                        'system_event',
                        f"System event: {entry.get('message')}",
                        entry
                    )
                    
        # Print real-time updates for important events
        if level in ['WARNING', 'ERROR', 'CRITICAL'] or event_type in ['battery', 'error', 'system']:
            timestamp = datetime.fromtimestamp(entry.get('timestamp', time.time()))
            component = entry.get('component', 'unknown')
            message = entry.get('message', 'No message')
            
            print(f"[{timestamp.strftime('%H:%M:%S')}] {component} | {level} | {message}")
            
    def _analyze_log_line(self, line: str, file_path: str):
        """Analyze standard log line for alerts"""
        line_lower = line.lower()
        
        # Check for error patterns
        if any(pattern in line_lower for pattern in ['error', 'exception', 'traceback', 'failed']):
            self._track_error_rate()
            
        # Check for critical patterns
        if any(pattern in line_lower for pattern in ['critical', 'fatal', 'crash', 'abort']):
            if self.alert_manager.should_alert('critical_log'):
                self.alert_manager.send_alert(
                    'critical_log',
                    f'Critical log entry in {pathlib.Path(file_path).name}',
                    {'line': line, 'file': file_path}
                )
                
        # Print real-time updates for important log lines
        if any(pattern in line_lower for pattern in ['error', 'warning', 'critical', 'exception']):
            timestamp = datetime.now().strftime('%H:%M:%S')
            filename = pathlib.Path(file_path).name
            print(f"[{timestamp}] {filename} | {line}")
            
    def _track_error_rate(self):
        """Track error rate and alert if threshold exceeded"""
        now = time.time()
        
        # Reset counter if window has passed
        if now - self.error_window_start >= 60:  # 1 minute window
            self.error_count = 0
            self.error_window_start = now
            
        self.error_count += 1
        
        # Check if error rate threshold exceeded
        if self.error_count >= self.error_threshold:
            if self.alert_manager.should_alert('high_error_rate'):
                self.alert_manager.send_alert(
                    'high_error_rate',
                    f'High error rate: {self.error_count} errors in last minute',
                    {'error_count': self.error_count, 'threshold': self.error_threshold}
                )
                
    def get_status(self) -> Dict:
        """Get current monitoring status"""
        return {
            'running': self.running,
            'monitored_files': len(self.file_positions),
            'last_battery_voltage': self.last_battery_voltage,
            'error_count_last_minute': self.error_count,
            'alert_stats': self.alert_manager.get_alert_stats()
        }


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down...")
    global monitor
    if monitor:
        monitor.stop()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Real-time log monitor for Blue Rover')
    parser.add_argument('--log-dir', type=pathlib.Path, 
                       default=pathlib.Path(__file__).parent.parent / 'logs',
                       help='Directory to monitor for log files')
    parser.add_argument('--battery-critical', type=float, default=3.0,
                       help='Critical battery voltage threshold')
    parser.add_argument('--battery-low', type=float, default=3.3,
                       help='Low battery voltage threshold')
    parser.add_argument('--error-threshold', type=int, default=5,
                       help='Error count threshold per minute')
    parser.add_argument('--alert-cooldown', type=int, default=60,
                       help='Cooldown between same alert types (seconds)')
    parser.add_argument('--status-interval', type=int, default=300,
                       help='Status report interval (seconds)')
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create alert manager
    alert_manager = AlertManager()
    alert_manager.alert_cooldown = args.alert_cooldown
    
    # Create and configure monitor
    global monitor
    monitor = LogMonitor(args.log_dir, alert_manager)
    monitor.battery_critical = args.battery_critical
    monitor.battery_low = args.battery_low
    monitor.error_threshold = args.error_threshold
    
    # Start monitoring
    monitor.start()
    
    # Status reporting thread
    def status_reporter():
        while monitor.running:
            time.sleep(args.status_interval)
            if monitor.running:
                status = monitor.get_status()
                print(f"\n--- Status Report ---")
                print(f"Monitored files: {status['monitored_files']}")
                print(f"Last battery voltage: {status['last_battery_voltage']}V")
                print(f"Errors last minute: {status['error_count_last_minute']}")
                print(f"Alert counts: {status['alert_stats']}")
                print("-------------------\n")
    
    status_thread = threading.Thread(target=status_reporter, daemon=True)
    status_thread.start()
    
    try:
        # Keep main thread alive
        while monitor.running:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop()


if __name__ == '__main__':
    main()