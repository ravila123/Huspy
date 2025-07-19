#!/usr/bin/env python3
"""
Blue Rover Battery Monitoring Module

Continuously monitors and logs battery voltage with comprehensive error handling,
configurable intervals, and alert thresholds for system health monitoring.

Features:
- Configurable monitoring intervals
- Low battery alerts
- Graceful error handling
- Structured logging
- Service-ready operation
"""

import logging
import signal
import sys
from dataclasses import dataclass
from time import sleep, time
from typing import Optional

try:
    from picarx import Picarx
except ImportError as e:
    logging.error(f"Failed to import PicarX module: {e}")
    sys.exit(1)

from src.utils.logutil import make_logger


@dataclass
class BatteryConfig:
    """Configuration for battery monitoring"""
    check_interval: float = 5.0  # seconds between checks
    low_battery_threshold: float = 6.5  # volts
    critical_battery_threshold: float = 6.0  # volts
    max_consecutive_errors: int = 5
    error_retry_delay: float = 10.0  # seconds


class BatteryMonitor:
    """Battery monitoring service for Blue Rover"""
    
    def __init__(self, config: Optional[BatteryConfig] = None):
        self.config = config or BatteryConfig()
        self.px: Optional[Picarx] = None
        self.logger = None
        self.log_file = None
        self.running = False
        self.consecutive_errors = 0
        self.last_voltage = None
        self.low_battery_warned = False
        self._setup_logging()
        self._setup_signal_handlers()
    
    def _setup_logging(self) -> None:
        """Initialize logging system"""
        try:
            self.logger, self.log_file = make_logger("battery")
            logging.info("Battery monitoring logging initialized")
        except Exception as e:
            logging.error(f"Failed to initialize logging: {e}")
            raise
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logging.info(f"Received signal {signum}, shutting down gracefully")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _log_event(self, event: str, v1: str = "", v2: str = "") -> None:
        """Log an event with error handling"""
        try:
            if self.logger:
                self.logger.writerow([time(), "batt", event, v1, v2])
                self.log_file.flush()
        except Exception as e:
            logging.warning(f"Failed to log event {event}: {e}")
    
    def initialize_hardware(self) -> bool:
        """Initialize hardware components with error handling"""
        try:
            self.px = Picarx()
            logging.info("PicarX initialized for battery monitoring")
            return True
        except Exception as e:
            logging.error(f"Hardware initialization failed: {e}")
            return False
    
    def get_battery_voltage(self) -> Optional[float]:
        """Get battery voltage with error handling"""
        if not self.px:
            logging.warning("Cannot read battery: PicarX not initialized")
            return None
        
        try:
            voltage = self.px.get_battery_voltage()
            if voltage is not None:
                self.consecutive_errors = 0
                return float(voltage)
            else:
                logging.warning("Battery voltage reading returned None")
                return None
                
        except AttributeError:
            logging.error("Battery voltage method not available on this hardware")
            return None
        except Exception as e:
            logging.error(f"Failed to read battery voltage: {e}")
            self.consecutive_errors += 1
            return None
    
    def check_battery_alerts(self, voltage: float) -> None:
        """Check for battery alert conditions"""
        if voltage <= self.config.critical_battery_threshold:
            alert_msg = f"CRITICAL: Battery voltage critically low: {voltage:.2f}V"
            logging.critical(alert_msg)
            print(alert_msg)
            self._log_event("critical_battery", str(voltage))
            
        elif voltage <= self.config.low_battery_threshold:
            if not self.low_battery_warned:
                alert_msg = f"WARNING: Battery voltage low: {voltage:.2f}V"
                logging.warning(alert_msg)
                print(alert_msg)
                self._log_event("low_battery", str(voltage))
                self.low_battery_warned = True
        else:
            # Reset warning flag when battery is above threshold
            if self.low_battery_warned:
                logging.info(f"Battery voltage recovered: {voltage:.2f}V")
                self.low_battery_warned = False
    
    def log_voltage_reading(self, voltage: Optional[float]) -> None:
        """Log voltage reading with appropriate level"""
        if voltage is not None:
            self._log_event("voltage", str(voltage))
            
            # Log significant voltage changes
            if self.last_voltage is not None:
                voltage_change = abs(voltage - self.last_voltage)
                if voltage_change > 0.5:  # Significant change threshold
                    logging.info(f"Significant voltage change: {self.last_voltage:.2f}V → {voltage:.2f}V")
            
            self.last_voltage = voltage
            logging.debug(f"Battery voltage: {voltage:.2f}V")
        else:
            self._log_event("voltage_error", "read_failed")
            logging.warning("Failed to read battery voltage")
    
    def handle_consecutive_errors(self) -> bool:
        """Handle consecutive error conditions
        
        Returns:
            bool: True to continue monitoring, False to stop
        """
        if self.consecutive_errors >= self.config.max_consecutive_errors:
            error_msg = f"Too many consecutive errors ({self.consecutive_errors}), stopping monitor"
            logging.error(error_msg)
            print(error_msg)
            return False
        
        if self.consecutive_errors > 0:
            logging.warning(f"Consecutive errors: {self.consecutive_errors}, retrying in {self.config.error_retry_delay}s")
            sleep(self.config.error_retry_delay)
        
        return True
    
    def shutdown(self) -> None:
        """Safely shutdown the monitor"""
        try:
            if self.log_file:
                self.log_file.close()
                logging.info("Battery monitor log file closed")
        except Exception as e:
            logging.warning(f"Error closing log file: {e}")
        
        logging.info("Battery monitor shutdown complete")
    
    def run(self) -> None:
        """Main monitoring loop"""
        if not self.initialize_hardware():
            print("Failed to initialize hardware. Exiting.")
            return
        
        logging.info("Battery monitoring started")
        print(f"Battery monitoring started (interval: {self.config.check_interval}s)")
        self.running = True
        
        try:
            while self.running:
                # Read battery voltage
                voltage = self.get_battery_voltage()
                
                # Log the reading
                self.log_voltage_reading(voltage)
                
                # Check for alerts if we have a valid reading
                if voltage is not None:
                    self.check_battery_alerts(voltage)
                
                # Handle error conditions
                if not self.handle_consecutive_errors():
                    break
                
                # Wait for next check
                sleep(self.config.check_interval)
                
        except KeyboardInterrupt:
            logging.info("Received keyboard interrupt")
        except Exception as e:
            logging.error(f"Unexpected error in monitoring loop: {e}")
        finally:
            self.shutdown()
            print("Battery monitoring stopped.")


def main():
    """Entry point for battery monitoring"""
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments for configuration
    import argparse
    parser = argparse.ArgumentParser(description='Blue Rover Battery Monitor')
    parser.add_argument('--interval', type=float, default=5.0,
                       help='Check interval in seconds (default: 5.0)')
    parser.add_argument('--low-threshold', type=float, default=6.5,
                       help='Low battery threshold in volts (default: 6.5)')
    parser.add_argument('--critical-threshold', type=float, default=6.0,
                       help='Critical battery threshold in volts (default: 6.0)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create configuration from arguments
    config = BatteryConfig(
        check_interval=args.interval,
        low_battery_threshold=args.low_threshold,
        critical_battery_threshold=args.critical_threshold
    )
    
    try:
        monitor = BatteryMonitor(config)
        monitor.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()