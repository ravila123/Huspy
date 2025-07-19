"""
Enhanced Logging System for Blue Rover

Provides structured logging with telemetry, real-time monitoring, alerts,
and automatic log rotation for the Blue Rover robotics system.
"""

import json
import logging
import logging.handlers
import pathlib
import threading
import time
import queue
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """Log severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventType(Enum):
    """Types of system events"""
    MOVEMENT = "movement"
    SYSTEM = "system"
    BATTERY = "battery"
    CAMERA = "camera"
    CONTROLLER = "controller"
    NETWORK = "network"
    ERROR = "error"


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: float
    component: str
    event_type: EventType
    level: LogLevel
    message: str
    data: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'component': self.component,
            'event_type': self.event_type.value,
            'level': self.level.value,
            'message': self.message,
            'data': self.data
        }


@dataclass
class AlertConfig:
    """Configuration for alerts"""
    battery_low_threshold: float = 3.3  # Volts
    battery_critical_threshold: float = 3.0  # Volts
    temperature_high_threshold: float = 70.0  # Celsius
    memory_usage_threshold: float = 90.0  # Percentage
    disk_usage_threshold: float = 85.0  # Percentage
    alert_cooldown: int = 300  # Seconds between same alert types


class LogRotationHandler(logging.handlers.RotatingFileHandler):
    """Custom rotating file handler with enhanced features"""
    
    def __init__(self, filename, max_bytes=10*1024*1024, backup_count=5):
        super().__init__(filename, maxBytes=max_bytes, backupCount=backup_count)
        self.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))


class RealTimeMonitor:
    """Real-time log monitoring and alerting"""
    
    def __init__(self, alert_config: AlertConfig, alert_callback: Optional[Callable] = None):
        self.alert_config = alert_config
        self.alert_callback = alert_callback or self._default_alert_handler
        self.last_alerts: Dict[str, float] = {}
        self.running = False
        self.monitor_thread = None
        
    def _default_alert_handler(self, alert_type: str, message: str, data: Dict[str, Any]):
        """Default alert handler - logs to system logger"""
        logging.critical(f"ALERT [{alert_type}]: {message} - Data: {data}")
        
    def should_send_alert(self, alert_type: str) -> bool:
        """Check if enough time has passed since last alert of this type"""
        now = time.time()
        last_alert = self.last_alerts.get(alert_type, 0)
        if now - last_alert >= self.alert_config.alert_cooldown:
            self.last_alerts[alert_type] = now
            return True
        return False
        
    def check_battery_alert(self, voltage: float):
        """Check for battery-related alerts"""
        if voltage <= self.alert_config.battery_critical_threshold:
            if self.should_send_alert("battery_critical"):
                self.alert_callback("battery_critical", 
                                  f"Critical battery level: {voltage}V", 
                                  {"voltage": voltage})
        elif voltage <= self.alert_config.battery_low_threshold:
            if self.should_send_alert("battery_low"):
                self.alert_callback("battery_low", 
                                  f"Low battery level: {voltage}V", 
                                  {"voltage": voltage})


class RoverLogger:
    """Enhanced logging system with structured data and real-time monitoring"""
    
    def __init__(self, 
                 component: str,
                 log_dir: Optional[pathlib.Path] = None,
                 alert_config: Optional[AlertConfig] = None,
                 alert_callback: Optional[Callable] = None):
        self.component = component
        self.log_dir = log_dir or (pathlib.Path(__file__).resolve().parents[2] / "logs")
        self.alert_config = alert_config or AlertConfig()
        
        # Ensure log directory exists
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
        # Set up logging infrastructure
        self.setup_logging()
        
        # Real-time monitoring
        self.monitor = RealTimeMonitor(self.alert_config, alert_callback)
        
        # Telemetry data storage
        self.telemetry_queue = queue.Queue(maxsize=1000)
        self.telemetry_thread = None
        self.running = False
        
        # Movement tracking
        self.movement_stats = {
            'total_distance': 0.0,
            'total_runtime': 0.0,
            'last_movement': None
        }
        
    def setup_logging(self):
        """Set up logging infrastructure"""
        # Create component-specific logger
        self.logger = logging.getLogger(f"rover.{self.component}")
        self.logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # File handler with rotation
        log_file = self.log_dir / f"{self.component}.log"
        file_handler = LogRotationHandler(str(log_file))
        file_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        
        # Console handler for real-time feedback
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
        ))
        self.logger.addHandler(console_handler)
        
        # JSON telemetry file
        self.telemetry_file = self.log_dir / f"{self.component}_telemetry.jsonl"
        
    def start_telemetry_logging(self):
        """Start background telemetry logging thread"""
        if self.running:
            return
            
        self.running = True
        self.telemetry_thread = threading.Thread(target=self._telemetry_worker, daemon=True)
        self.telemetry_thread.start()
        
    def stop_telemetry_logging(self):
        """Stop background telemetry logging"""
        self.running = False
        if self.telemetry_thread and self.telemetry_thread.is_alive():
            self.telemetry_thread.join(timeout=5.0)
            
    def _telemetry_worker(self):
        """Background worker for telemetry logging"""
        with open(self.telemetry_file, 'a', encoding='utf-8') as f:
            while self.running:
                try:
                    # Get telemetry entry with timeout
                    entry = self.telemetry_queue.get(timeout=1.0)
                    
                    # Write JSON line
                    json.dump(entry.to_dict(), f)
                    f.write('\n')
                    f.flush()
                    
                    self.telemetry_queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    self.logger.error(f"Telemetry logging error: {e}")
                    
    def _log_entry(self, event_type: EventType, level: LogLevel, message: str, data: Dict[str, Any]):
        """Create and process a log entry"""
        entry = LogEntry(
            timestamp=time.time(),
            component=self.component,
            event_type=event_type,
            level=level,
            message=message,
            data=data
        )
        
        # Log to standard logger
        log_level = getattr(logging, level.value)
        self.logger.log(log_level, f"{message} - {json.dumps(data)}")
        
        # Add to telemetry queue if running
        if self.running:
            try:
                self.telemetry_queue.put_nowait(entry)
            except queue.Full:
                self.logger.warning("Telemetry queue full, dropping entry")
                
        return entry
        
    def log_movement(self, action: str, speed: int, direction: int, duration: float = 0.0):
        """Log movement telemetry with structured data"""
        data = {
            'action': action,
            'speed': speed,
            'direction': direction,
            'duration': duration
        }
        
        # Update movement statistics
        if duration > 0:
            self.movement_stats['total_runtime'] += duration
            # Rough distance calculation (speed * time)
            self.movement_stats['total_distance'] += abs(speed) * duration / 100.0
            
        self.movement_stats['last_movement'] = time.time()
        
        return self._log_entry(EventType.MOVEMENT, LogLevel.INFO, 
                              f"Movement: {action}", data)
        
    def log_system_event(self, event: str, data: Dict[str, Any], level: LogLevel = LogLevel.INFO):
        """Log system events with context"""
        return self._log_entry(EventType.SYSTEM, level, f"System: {event}", data)
        
    def log_battery_status(self, voltage: float, percentage: Optional[float] = None):
        """Log battery status and check for alerts"""
        data = {'voltage': voltage}
        if percentage is not None:
            data['percentage'] = percentage
            
        # Check for battery alerts
        self.monitor.check_battery_alert(voltage)
        
        level = LogLevel.WARNING if voltage < 3.5 else LogLevel.INFO
        return self._log_entry(EventType.BATTERY, level, 
                              f"Battery: {voltage}V", data)
        
    def log_camera_event(self, event: str, data: Dict[str, Any]):
        """Log camera-related events"""
        return self._log_entry(EventType.CAMERA, LogLevel.INFO, 
                              f"Camera: {event}", data)
        
    def log_controller_event(self, event: str, data: Dict[str, Any]):
        """Log controller-related events"""
        return self._log_entry(EventType.CONTROLLER, LogLevel.INFO, 
                              f"Controller: {event}", data)
        
    def log_network_event(self, event: str, data: Dict[str, Any]):
        """Log network-related events"""
        return self._log_entry(EventType.NETWORK, LogLevel.INFO, 
                              f"Network: {event}", data)
        
    def log_error(self, error: str, exception: Optional[Exception] = None, data: Optional[Dict[str, Any]] = None):
        """Log errors with optional exception details"""
        error_data = data or {}
        if exception:
            error_data.update({
                'exception_type': type(exception).__name__,
                'exception_message': str(exception)
            })
            
        return self._log_entry(EventType.ERROR, LogLevel.ERROR, 
                              f"Error: {error}", error_data)
        
    def get_movement_stats(self) -> Dict[str, Any]:
        """Get movement statistics"""
        return self.movement_stats.copy()
        
    def get_recent_logs(self, minutes: int = 10, event_type: Optional[EventType] = None) -> List[Dict[str, Any]]:
        """Get recent log entries from telemetry file"""
        if not self.telemetry_file.exists():
            return []
            
        cutoff_time = time.time() - (minutes * 60)
        recent_logs = []
        
        try:
            with open(self.telemetry_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry['timestamp'] >= cutoff_time:
                            if event_type is None or entry['event_type'] == event_type.value:
                                recent_logs.append(entry)
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error reading recent logs: {e}")
            
        return sorted(recent_logs, key=lambda x: x['timestamp'], reverse=True)
        
    def cleanup_old_logs(self, days_to_keep: int = 7):
        """Clean up old log files"""
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    self.logger.info(f"Removed old log file: {log_file}")
            except Exception as e:
                self.logger.warning(f"Failed to remove old log file {log_file}: {e}")
                
        # Clean up old telemetry files
        for telemetry_file in self.log_dir.glob("*_telemetry.jsonl*"):
            try:
                if telemetry_file.stat().st_mtime < cutoff_time:
                    telemetry_file.unlink()
                    self.logger.info(f"Removed old telemetry file: {telemetry_file}")
            except Exception as e:
                self.logger.warning(f"Failed to remove old telemetry file {telemetry_file}: {e}")


# Global logger registry for easy access
_logger_registry: Dict[str, RoverLogger] = {}


def get_logger(component: str, **kwargs) -> RoverLogger:
    """Get or create a logger for a component"""
    if component not in _logger_registry:
        _logger_registry[component] = RoverLogger(component, **kwargs)
    return _logger_registry[component]


def start_all_telemetry():
    """Start telemetry logging for all registered loggers"""
    for logger in _logger_registry.values():
        logger.start_telemetry_logging()


def stop_all_telemetry():
    """Stop telemetry logging for all registered loggers"""
    for logger in _logger_registry.values():
        logger.stop_telemetry_logging()


def cleanup_all_logs(days_to_keep: int = 7):
    """Clean up old logs for all registered loggers"""
    for logger in _logger_registry.values():
        logger.cleanup_old_logs(days_to_keep)


# Signal handlers for graceful shutdown
def _signal_handler(signum, frame):
    """Handle shutdown signals"""
    print(f"\nReceived signal {signum}, shutting down telemetry logging...")
    stop_all_telemetry()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


if __name__ == "__main__":
    # Example usage and testing
    logger = get_logger("test")
    logger.start_telemetry_logging()
    
    # Test different log types
    logger.log_movement("forward", 50, 0, 2.5)
    logger.log_battery_status(3.7, 75.0)
    logger.log_system_event("startup", {"version": "1.0.0"})
    logger.log_camera_event("stream_started", {"resolution": "720p", "fps": 30})
    logger.log_controller_event("connected", {"controller_type": "PS5"})
    logger.log_network_event("wifi_connected", {"ssid": "RoverNet", "signal": -45})
    logger.log_error("Test error", ValueError("Test exception"), {"context": "testing"})
    
    # Wait a bit for telemetry to process
    time.sleep(2)
    
    # Get recent logs
    recent = logger.get_recent_logs(1)
    print(f"Recent logs: {len(recent)} entries")
    
    # Get movement stats
    stats = logger.get_movement_stats()
    print(f"Movement stats: {stats}")
    
    logger.stop_telemetry_logging()