#!/usr/bin/env python3
"""
Blue Rover PS5 DualSense Controller Module

Drive PiCar-X with a PlayStation 5 DualSense controller with improved
error handling, logging, and configuration management.

Controls:
• Left-stick X  : steering (−35° … +35°)
• R2            : forward throttle  (0–100 %)
• L2            : reverse throttle  (0–100 %)
• Right-stick   : camera pan / tilt
• □ (square)    : full stop
• Options       : quit

Requires:
    python3 -m pip install pydualsense
"""

import logging
import sys
from dataclasses import dataclass
from time import sleep, time
from typing import Optional, Dict, Any

try:
    from pydualsense import pydualsense, CallbackType
    from picarx import Picarx
except ImportError as e:
    logging.error(f"Failed to import required modules: {e}")
    sys.exit(1)

from src.utils.logutil import make_logger


@dataclass
class PS5Config:
    """Configuration for PS5 controller interface"""
    steer_max: int = 35
    pan_max: int = 35
    tilt_max: int = 35
    camera_sensitivity: float = 2.0
    deadzone_threshold: int = 10
    connection_timeout: float = 5.0


@dataclass
class RoverState:
    """Current state of the rover"""
    speed: int = 0
    direction: int = 1  # 1 forward, -1 reverse
    steer: int = 0
    pan: int = 0
    tilt: int = 0


class PS5RoverController:
    """PS5 DualSense controller interface for Blue Rover"""
    
    def __init__(self, config: Optional[PS5Config] = None):
        self.config = config or PS5Config()
        self.state = RoverState()
        self.px: Optional[Picarx] = None
        self.ds: Optional[pydualsense] = None
        self.logger = None
        self.log_file = None
        self.running = False
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Initialize logging system"""
        try:
            self.logger, self.log_file = make_logger("ps5_drive")
            logging.info("PS5 control logging initialized")
        except Exception as e:
            logging.error(f"Failed to initialize logging: {e}")
            raise
    
    def _log_event(self, event: str, v1: str = "", v2: str = "") -> None:
        """Log an event with error handling"""
        try:
            if self.logger:
                self.logger.writerow([time(), "ps5", event, v1, v2])
                self.log_file.flush()
        except Exception as e:
            logging.warning(f"Failed to log event {event}: {e}")
    
    def initialize_hardware(self) -> bool:
        """Initialize hardware components with error handling"""
        try:
            # Initialize PicarX
            self.px = Picarx()
            logging.info("PicarX initialized successfully")
            
            # Initialize PS5 controller
            self.ds = pydualsense()
            self.ds.init()
            
            if not self.ds.connected():
                logging.error("DualSense controller not found")
                print("DualSense not found. Please pair over Bluetooth or connect via USB-C.")
                return False
            
            logging.info("DualSense controller connected successfully")
            self._setup_callbacks()
            return True
            
        except Exception as e:
            logging.error(f"Hardware initialization failed: {e}")
            return False
    
    def _setup_callbacks(self) -> None:
        """Setup PS5 controller callbacks"""
        if not self.ds:
            return
            
        try:
            self.ds.callback_station(CallbackType.BUTTONS, self._on_buttons)
            self.ds.callback_station(CallbackType.TRIGGERS, self._on_triggers)
            self.ds.callback_station(CallbackType.STICKS, self._on_sticks)
            logging.info("PS5 controller callbacks registered")
        except Exception as e:
            logging.error(f"Failed to setup callbacks: {e}")
            raise
    
    def _on_buttons(self, btn: Dict[str, Any]) -> None:
        """Handle button press events"""
        try:
            if btn.get("square"):
                # Emergency stop
                self.state.speed = 0
                if self.px:
                    self.px.stop()
                self._log_event("emergency_stop")
                logging.info("Emergency stop activated")
            
            if btn.get("options"):
                # Quit application
                self.running = False
                self._log_event("quit_requested")
                logging.info("Quit requested via Options button")
                
        except Exception as e:
            logging.error(f"Error in button callback: {e}")
    
    def _on_triggers(self, trg: Dict[str, Any]) -> None:
        """Handle trigger events for throttle control"""
        try:
            r2_value = trg.get("r2", 0)
            l2_value = trg.get("l2", 0)
            
            if r2_value > self.config.deadzone_threshold:
                # Forward throttle
                self.state.direction = 1
                self.state.speed = int(r2_value * 100 / 255)
            elif l2_value > self.config.deadzone_threshold:
                # Reverse throttle
                self.state.direction = -1
                self.state.speed = int(l2_value * 100 / 255)
            else:
                # No throttle input
                self.state.speed = 0
            
            self._apply_motion()
            self._log_event("speed", str(self.state.direction * self.state.speed))
            
        except Exception as e:
            logging.error(f"Error in trigger callback: {e}")
    
    def _on_sticks(self, stk: Dict[str, Any]) -> None:
        """Handle stick events for steering and camera control"""
        try:
            # Left stick X for steering
            lx_value = stk.get("lx", 0)
            if abs(lx_value) > self.config.deadzone_threshold:
                self.state.steer = int(lx_value * self.config.steer_max / 127)
            else:
                self.state.steer = 0
            
            # Right stick for camera control
            rx_value = stk.get("rx", 0)
            ry_value = stk.get("ry", 0)
            
            if abs(rx_value) > self.config.deadzone_threshold:
                pan_delta = int(rx_value / 127 * self.config.camera_sensitivity)
                self.state.pan = max(-self.config.pan_max, 
                                   min(self.config.pan_max, 
                                       self.state.pan + pan_delta))
            
            if abs(ry_value) > self.config.deadzone_threshold:
                tilt_delta = -int(ry_value / 127 * self.config.camera_sensitivity)
                self.state.tilt = max(-self.config.tilt_max, 
                                    min(self.config.tilt_max, 
                                        self.state.tilt + tilt_delta))
            
            self._apply_motion()
            self._log_event("steer_cam", str(self.state.steer), 
                          f"pan:{self.state.pan},tilt:{self.state.tilt}")
            
        except Exception as e:
            logging.error(f"Error in stick callback: {e}")
    
    def _apply_motion(self) -> None:
        """Apply current state to hardware with error handling"""
        if not self.px:
            logging.warning("Cannot apply motion: PicarX not initialized")
            return
        
        try:
            # Apply steering
            self.px.set_dir_servo_angle(self.state.steer)
            
            # Apply throttle
            if self.state.speed == 0:
                self.px.stop()
            elif self.state.direction == 1:
                self.px.forward(self.state.speed)
            else:
                self.px.backward(self.state.speed)
            
            # Apply camera position
            self.px.set_cam_pan_angle(self.state.pan)
            self.px.set_cam_tilt_angle(self.state.tilt)
            
        except Exception as e:
            logging.error(f"Failed to apply motion commands: {e}")
            # Emergency stop on error
            try:
                if self.px:
                    self.px.stop()
            except:
                pass
    
    def shutdown_hardware(self) -> None:
        """Safely shutdown all hardware components"""
        try:
            if self.px:
                self.px.stop()
                self.px.set_dir_servo_angle(0)
                self.px.set_cam_pan_angle(0)
                self.px.set_cam_tilt_angle(0)
                logging.info("PicarX shutdown complete")
        except Exception as e:
            logging.warning(f"Error during PicarX shutdown: {e}")
        
        try:
            if self.ds:
                self.ds.close()
                logging.info("DualSense controller disconnected")
        except Exception as e:
            logging.warning(f"Error during controller shutdown: {e}")
        
        try:
            if self.log_file:
                self.log_file.close()
                logging.info("Log file closed")
        except Exception as e:
            logging.warning(f"Error closing log file: {e}")
    
    def run(self) -> None:
        """Main control loop"""
        if not self.initialize_hardware():
            print("Failed to initialize hardware. Exiting.")
            return
        
        print("DualSense connected. Drive away! (Options button = quit)")
        self.running = True
        
        try:
            while self.running:
                # Check controller connection
                if not self.ds or not self.ds.connected():
                    logging.warning("Controller disconnected")
                    break
                
                sleep(0.1)  # Prevent busy waiting
                
        except KeyboardInterrupt:
            logging.info("Received keyboard interrupt")
        except Exception as e:
            logging.error(f"Unexpected error in main loop: {e}")
        finally:
            self.shutdown_hardware()
            print("PS5 control shutdown complete.")


def main():
    """Entry point for PS5 control"""
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        controller = PS5RoverController()
        controller.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()