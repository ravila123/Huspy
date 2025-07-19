"""
Enhanced Logging Utility for Blue Rover

Provides structured CSV logging with proper error handling, configuration
management, and log rotation capabilities.

This module provides backward compatibility with the legacy CSV logging
while integrating with the new enhanced logging system.
"""

import csv
import logging
import pathlib
import time
from typing import Optional, Tuple, TextIO

# Import the new enhanced logging system
try:
    from .enhanced_logging import get_logger, LogLevel, EventType
    ENHANCED_LOGGING_AVAILABLE = True
except ImportError:
    ENHANCED_LOGGING_AVAILABLE = False


class LogConfig:
    """Configuration for logging system"""
    def __init__(self, 
                 log_dir: Optional[pathlib.Path] = None,
                 max_log_size: int = 10 * 1024 * 1024,  # 10MB
                 max_log_files: int = 5):
        self.log_dir = log_dir or (pathlib.Path(__file__).resolve().parents[1] / "logs")
        self.max_log_size = max_log_size
        self.max_log_files = max_log_files
        
        # Ensure log directory exists
        try:
            self.log_dir.mkdir(exist_ok=True, parents=True)
        except Exception as e:
            logging.error(f"Failed to create log directory {self.log_dir}: {e}")
            raise


def cleanup_old_logs(log_dir: pathlib.Path, prefix: str, max_files: int = 5) -> None:
    """Clean up old log files, keeping only the most recent ones"""
    try:
        log_files = list(log_dir.glob(f"{prefix}-*.csv"))
        if len(log_files) > max_files:
            # Sort by modification time, oldest first
            log_files.sort(key=lambda f: f.stat().st_mtime)
            
            # Remove oldest files
            for old_file in log_files[:-max_files]:
                try:
                    old_file.unlink()
                    logging.debug(f"Removed old log file: {old_file}")
                except Exception as e:
                    logging.warning(f"Failed to remove old log file {old_file}: {e}")
                    
    except Exception as e:
        logging.warning(f"Failed to cleanup old logs: {e}")


class EnhancedCSVLogger:
    """
    Enhanced CSV logger that integrates with the new logging system
    """
    
    def __init__(self, prefix: str = "log", config: Optional[LogConfig] = None):
        self.prefix = prefix
        self.config = config or LogConfig()
        
        # Set up enhanced logger if available
        if ENHANCED_LOGGING_AVAILABLE:
            self.enhanced_logger = get_logger(f"csv_{prefix}")
        else:
            self.enhanced_logger = None
            
        # Set up CSV logging
        self.csv_writer, self.file_handle = self._create_csv_logger()
        
    def _create_csv_logger(self) -> Tuple[csv.writer, TextIO]:
        """Create CSV logger"""
        try:
            # Clean up old logs
            cleanup_old_logs(self.config.log_dir, self.prefix, self.config.max_log_files)
            
            # Create new log file
            timestamp = int(time.time())
            fname = self.config.log_dir / f"{self.prefix}-{timestamp}.csv"
            
            # Open file with proper error handling
            f = open(fname, "w", newline="", encoding='utf-8')
            csvw = csv.writer(f)
            
            # Write header
            csvw.writerow(["timestamp", "source", "event", "value1", "value2"])
            f.flush()
            
            logging.info(f"Created CSV log file: {fname}")
            return csvw, f
            
        except Exception as e:
            error_msg = f"Failed to create CSV logger with prefix '{self.prefix}': {e}"
            logging.error(error_msg)
            raise Exception(error_msg) from e
            
    def log(self, source: str, event: str, value1: str = "", value2: str = "") -> bool:
        """
        Log an entry to both CSV and enhanced logging system
        
        Returns:
            bool: True if successful, False otherwise
        """
        timestamp = time.time()
        
        # Log to CSV
        csv_success = self._log_to_csv(timestamp, source, event, value1, value2)
        
        # Log to enhanced system if available
        if self.enhanced_logger:
            try:
                # Determine event type based on source/event
                event_type = self._determine_event_type(source, event)
                data = {
                    'source': source,
                    'event': event,
                    'value1': value1,
                    'value2': value2
                }
                
                # Log to enhanced system
                if event_type == EventType.MOVEMENT:
                    # Try to parse movement data
                    try:
                        speed = int(value1) if value1.isdigit() else 0
                        direction = int(value2) if value2.lstrip('-').isdigit() else 0
                        self.enhanced_logger.log_movement(event, speed, direction)
                    except:
                        self.enhanced_logger.log_system_event(f"CSV: {event}", data)
                elif event_type == EventType.BATTERY:
                    # Try to parse battery data
                    try:
                        voltage = float(value1) if value1.replace('.', '').isdigit() else 0
                        self.enhanced_logger.log_battery_status(voltage)
                    except:
                        self.enhanced_logger.log_system_event(f"CSV: {event}", data)
                else:
                    self.enhanced_logger.log_system_event(f"CSV: {event}", data)
                    
            except Exception as e:
                logging.warning(f"Failed to log to enhanced system: {e}")
                
        return csv_success
        
    def _log_to_csv(self, timestamp: float, source: str, event: str, value1: str, value2: str) -> bool:
        """Log to CSV file"""
        try:
            self.csv_writer.writerow([timestamp, source, event, value1, value2])
            self.file_handle.flush()
            return True
        except Exception as e:
            logging.warning(f"Failed to write CSV log entry: {e}")
            return False
            
    def _determine_event_type(self, source: str, event: str) -> EventType:
        """Determine event type from source and event"""
        source_lower = source.lower()
        event_lower = event.lower()
        
        if any(keyword in source_lower or keyword in event_lower 
               for keyword in ['move', 'forward', 'backward', 'turn', 'speed']):
            return EventType.MOVEMENT
        elif any(keyword in source_lower or keyword in event_lower 
                 for keyword in ['battery', 'voltage', 'power']):
            return EventType.BATTERY
        elif any(keyword in source_lower or keyword in event_lower 
                 for keyword in ['camera', 'stream', 'video']):
            return EventType.CAMERA
        elif any(keyword in source_lower or keyword in event_lower 
                 for keyword in ['controller', 'ps5', 'button']):
            return EventType.CONTROLLER
        elif any(keyword in source_lower or keyword in event_lower 
                 for keyword in ['error', 'exception', 'fail']):
            return EventType.ERROR
        else:
            return EventType.SYSTEM
            
    def close(self):
        """Close the logger"""
        if self.file_handle:
            self.file_handle.close()


def make_logger(prefix: str = "log", 
                config: Optional[LogConfig] = None) -> Tuple[csv.writer, TextIO]:
    """
    Create a CSV logger with proper error handling and configuration
    
    Args:
        prefix: Prefix for the log filename
        config: Optional logging configuration
        
    Returns:
        Tuple of (csv.writer, file_handle)
        
    Raises:
        Exception: If logger creation fails
    """
    if config is None:
        config = LogConfig()
    
    try:
        # Clean up old logs
        cleanup_old_logs(config.log_dir, prefix, config.max_log_files)
        
        # Create new log file
        timestamp = int(time.time())
        fname = config.log_dir / f"{prefix}-{timestamp}.csv"
        
        # Open file with proper error handling
        f = open(fname, "w", newline="", encoding='utf-8')
        csvw = csv.writer(f)
        
        # Write header
        csvw.writerow(["timestamp", "source", "event", "value1", "value2"])
        f.flush()
        
        logging.info(f"Created log file: {fname}")
        return csvw, f
        
    except Exception as e:
        error_msg = f"Failed to create logger with prefix '{prefix}': {e}"
        logging.error(error_msg)
        raise Exception(error_msg) from e


def safe_log_write(logger: csv.writer, 
                   log_file: TextIO,
                   timestamp: float,
                   source: str,
                   event: str,
                   value1: str = "",
                   value2: str = "") -> bool:
    """
    Safely write to log with error handling
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.writerow([timestamp, source, event, value1, value2])
        log_file.flush()
        return True
    except Exception as e:
        logging.warning(f"Failed to write log entry: {e}")
        return False


# Legacy compatibility function
def make_logger_legacy(prefix: str = "log") -> Tuple[csv.writer, TextIO]:
    """Legacy compatibility wrapper for make_logger"""
    return make_logger(prefix)


# Enhanced logger factory function
def get_enhanced_csv_logger(prefix: str = "log", config: Optional[LogConfig] = None) -> EnhancedCSVLogger:
    """
    Get an enhanced CSV logger that integrates with the new logging system
    
    Args:
        prefix: Prefix for the log filename
        config: Optional logging configuration
        
    Returns:
        EnhancedCSVLogger instance
    """
    return EnhancedCSVLogger(prefix, config)
