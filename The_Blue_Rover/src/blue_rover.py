#!/usr/bin/env python3
"""
Blue Rover Manual Control Module

Provides keyboard-based manual control for the Blue Rover with comprehensive
error handling, logging, and configuration management.

Controls:
  w / s : bump +10 % speed forward / reverse
  x     : full stop
  a / d : steer left / right  (–35 ° / +35 °)
  i / k : camera tilt  up / down  (±35 °)
  j / l : camera pan   left / right (±35 °)
  t     : snapshot  (saved to logs/)
  q     : quit

Live video  →  http://<Pi-IP>:8080/stream.mjpg
CSV logs   →  logs/drive-<timestamp>.csv
"""

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from time import sleep, time
from typing import Optional, Tuple

try:
    from picarx import Picarx
    from vilib import Vilib
    import readchar
except ImportError as e:
    logging.error(f"Failed to import required hardware modules: {e}")
    sys.exit(1)

from src.utils.logutil import make_logger


@dataclass
class RoverConfig:
    """Configuration for Blue Rover manual control"""
    max_speed: int = 100
    speed_increment: int = 10
    steer_max: int = 35
    tilt_max: int = 35
    pan_max: int = 35
    camera_step: int = 5
    loop_delay: float = 0.05
    camera_warmup_time: float = 2.0


@dataclass
class RoverState:
    """Current state of the rover"""
    speed: int = 0
    dir_fwd: int = 1  # 1 forward, -1 reverse
    steer: int = 0
    pan: int = 0
    tilt: int = 0


class BlueRoverController:
    """Main controller class for Blue Rover manual operation"""
    
    def __init__(self, config: Optional[RoverConfig] = None):
        self.config = config or RoverConfig()
        self.state = RoverState()
        self.px: Optional[Picarx] = None
        self.logger = None
        self.log_file = None
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """Initialize logging system"""
        try:
            self.logger, self.log_file = make_logger("manual_drive")
            logging.info("Manual control logging initialized")
        except Exception as e:
            logging.error(f"Failed to initialize logging: {e}")
            raise
    
    def _log_event(self, event: str, v1: str = "", v2: str = "") -> None:
        """Log an event with error handling"""
        try:
            if self.logger:
                self.logger.writerow([time(), "kbd", event, v1, v2])
                self.log_file.flush()
        except Exception as e:
            logging.warning(f"Failed to log event {event}: {e}")
    
    def initialize_hardware(self) -> bool:
        """Initialize hardware components with error handling"""
        try:
            # Initialize PicarX
            self.px = Picarx()
            logging.info("PicarX initialized successfully")
            
            # Initialize camera
            Vilib.camera_start(vflip=False, hflip=False)
            Vilib.display(local=True, web=True)
            sleep(self.config.camera_warmup_time)
            logging.info("Camera system initialized successfully")
            
            return True
            
        except Exception as e:
            logging.error(f"Hardware initialization failed: {e}")
            return False
    
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
            Vilib.camera_close()
            logging.info("Camera shutdown complete")
        except Exception as e:
            logging.warning(f"Error during camera shutdown: {e}")
        
        try:
            if self.log_file:
                self.log_file.close()
                logging.info("Log file closed")
        except Exception as e:
            logging.warning(f"Error closing log file: {e}")
    
    def apply_drive_commands(self) -> None:
        """Apply current drive state to hardware with error handling"""
        if not self.px:
            logging.warning("Cannot apply drive commands: PicarX not initialized")
            return
            
        try:
            # Apply steering
            self.px.set_dir_servo_angle(self.state.steer)
            
            # Apply speed and direction
            if self.state.speed == 0:
                self.px.stop()
            elif self.state.dir_fwd == 1:
                self.px.forward(self.state.speed)
            else:
                self.px.backward(self.state.speed)
                
        except Exception as e:
            logging.error(f"Failed to apply drive commands: {e}")
            # Emergency stop on error
            try:
                self.px.stop()
            except:
                pass
    
    def apply_camera_commands(self) -> None:
        """Apply camera position commands with error handling"""
        if not self.px:
            logging.warning("Cannot apply camera commands: PicarX not initialized")
            return
            
        try:
            self.px.set_cam_pan_angle(self.state.pan)
            self.px.set_cam_tilt_angle(self.state.tilt)
        except Exception as e:
            logging.error(f"Failed to apply camera commands: {e}")
    
    def take_snapshot(self) -> bool:
        """Take a photo snapshot with error handling"""
        try:
            fname = f"cap-{int(time())}"
            log_dir = Path(__file__).resolve().parents[1] / "logs"
            Vilib.take_photo(fname, str(log_dir) + "/")
            
            snapshot_path = log_dir / f"{fname}.jpg"
            print(f"Saved {snapshot_path}")
            self._log_event("snap", f"{fname}.jpg")
            logging.info(f"Snapshot saved: {snapshot_path}")
            return True
            
        except Exception as e:
            error_msg = f"Snapshot failed: {e}"
            print(error_msg)
            logging.error(error_msg)
            return False
    
    def process_key_input(self, key: str) -> bool:
        """Process keyboard input and update rover state
        
        Returns:
            bool: True to continue, False to quit
        """
        if key in ('q', readchar.key.CTRL_C):
            return False
        
        # Speed and direction controls
        if key == 'w':
            self.state.dir_fwd = 1
            self.state.speed = min(self.state.speed + self.config.speed_increment, 
                                 self.config.max_speed)
            self._log_event(key, self.state.dir_fwd * self.state.speed)
            
        elif key == 's':
            self.state.dir_fwd = -1
            self.state.speed = min(self.state.speed + self.config.speed_increment, 
                                 self.config.max_speed)
            self._log_event(key, self.state.dir_fwd * self.state.speed)
            
        elif key == 'x':
            self.state.speed = 0
            self._log_event(key, 0)
        
        # Steering controls
        elif key == 'a':
            self.state.steer = -self.config.steer_max
            self._log_event(key, self.state.steer)
            
        elif key == 'd':
            self.state.steer = self.config.steer_max
            self._log_event(key, self.state.steer)
            
        elif key in ('w', 's', 'x'):  # Straighten when only throttle changes
            self.state.steer = 0
        
        # Camera controls
        elif key == 'i':
            self.state.tilt = min(self.state.tilt + self.config.camera_step, 
                                self.config.tilt_max)
            self._log_event(key, self.state.tilt)
            
        elif key == 'k':
            self.state.tilt = max(self.state.tilt - self.config.camera_step, 
                                -self.config.tilt_max)
            self._log_event(key, self.state.tilt)
            
        elif key == 'j':
            self.state.pan = max(self.state.pan - self.config.camera_step, 
                               -self.config.pan_max)
            self._log_event(key, self.state.pan)
            
        elif key == 'l':
            self.state.pan = min(self.state.pan + self.config.camera_step, 
                               self.config.pan_max)
            self._log_event(key, self.state.pan)
        
        # Snapshot
        elif key == 't':
            self.take_snapshot()
        
        return True
    
    def display_help(self) -> None:
        """Display help information"""
        help_text = """
Blue Rover Manual Control
========================
w/s = speed ±10% (forward/reverse)
x   = stop
a/d = steer left/right
i/k = tilt camera up/down
j/l = pan camera left/right
t   = snapshot
q   = quit
"""
        print("\033[H\033[J" + help_text)
    
    def run(self) -> None:
        """Main control loop"""
        if not self.initialize_hardware():
            print("Failed to initialize hardware. Exiting.")
            return
        
        self.display_help()
        
        try:
            while True:
                try:
                    key = readchar.readkey().lower()
                    
                    if not self.process_key_input(key):
                        break
                    
                    # Apply all commands
                    self.apply_drive_commands()
                    self.apply_camera_commands()
                    
                    sleep(self.config.loop_delay)
                    
                except readchar.ReadCharError as e:
                    logging.warning(f"Key reading error: {e}")
                    continue
                except Exception as e:
                    logging.error(f"Unexpected error in main loop: {e}")
                    break
                    
        except KeyboardInterrupt:
            logging.info("Received keyboard interrupt")
        finally:
            self.shutdown_hardware()
            print("Shutdown complete; logs saved in logs/")


def main():
    """Entry point for manual control"""
    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        controller = BlueRoverController()
        controller.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()