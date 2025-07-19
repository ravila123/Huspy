#!/usr/bin/env python3
"""
Blue Rover Camera Streaming Service

Provides standalone camera streaming functionality for the Blue Rover system.
This service runs independently and provides a web-accessible camera stream.

Features:
- Web-based camera streaming on port 8080
- Configurable camera settings
- Graceful shutdown handling
- Service-ready operation
- Error recovery and logging
"""

import logging
import signal
import sys
import time
from dataclasses import dataclass
from typing import Optional

try:
    from vilib import Vilib
except ImportError as e:
    logging.error(f"Failed to import Vilib camera module: {e}")
    sys.exit(1)


@dataclass
class CameraConfig:
    """Configuration for camera streaming"""
    web_port: int = 8080
    vflip: bool = False
    hflip: bool = False
    warmup_time: float = 2.0
    local_display: bool = True
    web_display: bool = True


class CameraStreamService:
    """Standalone camera streaming service"""
    
    def __init__(self, config: Optional[CameraConfig] = None):
        self.config = config or CameraConfig()
        self.running = False
        self._setup_logging()
        self._setup_signal_handlers()
    
    def _setup_logging(self) -> None:
        """Initialize logging system"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('camera_stream')
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def initialize_camera(self) -> bool:
        """Initialize camera system with error handling"""
        try:
            self.logger.info("Initializing camera system...")
            
            # Start camera with configuration
            Vilib.camera_start(
                vflip=self.config.vflip,
                hflip=self.config.hflip
            )
            
            # Enable display modes
            Vilib.display(
                local=self.config.local_display,
                web=self.config.web_display
            )
            
            # Allow camera to warm up
            time.sleep(self.config.warmup_time)
            
            self.logger.info(f"Camera streaming available at http://localhost:{self.config.web_port}/stream.mjpg")
            return True
            
        except Exception as e:
            self.logger.error(f"Camera initialization failed: {e}")
            return False
    
    def shutdown_camera(self) -> None:
        """Safely shutdown camera system"""
        try:
            self.logger.info("Shutting down camera system...")
            Vilib.camera_close()
            self.logger.info("Camera shutdown complete")
        except Exception as e:
            self.logger.warning(f"Error during camera shutdown: {e}")
    
    def run(self) -> None:
        """Main service loop"""
        if not self.initialize_camera():
            self.logger.error("Failed to initialize camera. Exiting.")
            sys.exit(1)
        
        self.logger.info("Camera streaming service started")
        self.running = True
        
        try:
            # Main service loop - just keep the service alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Unexpected error in service loop: {e}")
        finally:
            self.shutdown_camera()
            self.logger.info("Camera streaming service stopped")


def main():
    """Entry point for camera streaming service"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Blue Rover Camera Streaming Service')
    parser.add_argument('--port', type=int, default=8080,
                       help='Web streaming port (default: 8080)')
    parser.add_argument('--vflip', action='store_true',
                       help='Flip camera vertically')
    parser.add_argument('--hflip', action='store_true',
                       help='Flip camera horizontally')
    parser.add_argument('--no-local', action='store_true',
                       help='Disable local display')
    parser.add_argument('--no-web', action='store_true',
                       help='Disable web streaming')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create configuration from arguments
    config = CameraConfig(
        web_port=args.port,
        vflip=args.vflip,
        hflip=args.hflip,
        local_display=not args.no_local,
        web_display=not args.no_web
    )
    
    try:
        service = CameraStreamService(config)
        service.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()