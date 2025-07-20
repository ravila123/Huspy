"""
Blue Rover Configuration Management System

This module provides dataclass-based configuration with JSON/YAML loading,
validation, and environment-specific overrides.
"""

import json
import os
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


@dataclass
class CameraConfig:
    """Camera-specific configuration"""
    enabled: bool = True
    port: int = 8080
    resolution_width: int = 640
    resolution_height: int = 480
    framerate: int = 30
    quality: int = 85
    flip_horizontal: bool = False
    flip_vertical: bool = False


@dataclass
class ControlConfig:
    """Control system configuration"""
    max_speed: int = 100
    steering_range: int = 35
    acceleration_rate: float = 0.8
    deceleration_rate: float = 0.9
    deadzone_threshold: float = 0.1
    ps5_controller_timeout: int = 30


@dataclass
class BatteryConfig:
    """Battery monitoring configuration"""
    check_interval: int = 5
    low_voltage_threshold: float = 6.5
    critical_voltage_threshold: float = 6.0
    enable_alerts: bool = True
    shutdown_on_critical: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "logs/rover.log"
    max_log_size_mb: int = 10
    backup_count: int = 5
    enable_telemetry: bool = True


@dataclass
class NetworkConfig:
    """Network and SSH configuration"""
    ssh_port: int = 22
    web_interface_port: int = 8000
    enable_web_interface: bool = True
    allowed_ssh_users: list = field(default_factory=lambda: ["pi"])
    connection_timeout: int = 30


@dataclass
class HardwareConfig:
    """Hardware-specific configuration"""
    enable_hardware: bool = True
    mock_hardware: bool = False
    i2c_bus: int = 1
    servo_frequency: int = 50
    motor_calibration: Dict[str, float] = field(default_factory=lambda: {
        "left_motor_offset": 0.0,
        "right_motor_offset": 0.0,
        "steering_center": 0.0
    })


@dataclass
class YOLODetectionConfig:
    """YOLO object detection configuration"""
    enabled: bool = True
    model_path: str = "models/yolov5n.pt"
    confidence_threshold: float = 0.5
    nms_threshold: float = 0.4
    input_size: list = field(default_factory=lambda: [640, 640])
    target_fps: int = 10
    enabled_classes: list = field(default_factory=lambda: ["person", "car", "bicycle", "dog", "cat"])
    device: str = "cpu"
    alerts: Dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "alert_classes": ["person", "dog"],
        "confidence_threshold": 0.7,
        "rate_limit_seconds": 30,
        "max_alerts_per_minute": 10
    })
    performance: Dict[str, Any] = field(default_factory=lambda: {
        "max_cpu_usage": 80,
        "adaptive_fps": True,
        "use_hardware_acceleration": True,
        "max_memory_mb": 1024,
        "frame_buffer_size": 5,
        "processing_threads": 2
    })


@dataclass
class RoverConfig:
    """Main rover configuration with all subsystem configs"""
    
    # Subsystem configurations
    camera: CameraConfig = field(default_factory=CameraConfig)
    control: ControlConfig = field(default_factory=ControlConfig)
    battery: BatteryConfig = field(default_factory=BatteryConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    yolo_detection: YOLODetectionConfig = field(default_factory=YOLODetectionConfig)
    
    # Global settings
    environment: str = "production"
    debug_mode: bool = False
    auto_start_services: bool = True
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'RoverConfig':
        """
        Load configuration from JSON or YAML file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            RoverConfig instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file format is invalid
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
            
            return cls.from_dict(data)
            
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"Invalid configuration file format: {e}")
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RoverConfig':
        """
        Create RoverConfig from dictionary
        
        Args:
            data: Configuration dictionary
            
        Returns:
            RoverConfig instance
        """
        # Create subsystem configs
        camera_config = CameraConfig(**data.get('camera', {}))
        control_config = ControlConfig(**data.get('control', {}))
        battery_config = BatteryConfig(**data.get('battery', {}))
        logging_config = LoggingConfig(**data.get('logging', {}))
        network_config = NetworkConfig(**data.get('network', {}))
        hardware_config = HardwareConfig(**data.get('hardware', {}))
        yolo_detection_config = YOLODetectionConfig(**data.get('yolo_detection', {}))
        
        # Extract global settings
        global_settings = {k: v for k, v in data.items() 
                          if k not in ['camera', 'control', 'battery', 'logging', 'network', 'hardware', 'yolo_detection']}
        
        return cls(
            camera=camera_config,
            control=control_config,
            battery=battery_config,
            logging=logging_config,
            network=network_config,
            hardware=hardware_config,
            yolo_detection=yolo_detection_config,
            **global_settings
        )
    
    @classmethod
    def from_environment(cls, env_name: str = None) -> 'RoverConfig':
        """
        Load configuration with environment-specific overrides
        
        Args:
            env_name: Environment name (development, testing, production)
            
        Returns:
            RoverConfig instance with environment overrides applied
        """
        if env_name is None:
            env_name = os.getenv('ROVER_ENV', 'production')
        
        # Start with default configuration
        config = cls()
        config.environment = env_name
        
        # Load base configuration if it exists
        base_config_path = Path('config/rover_config.json')
        if base_config_path.exists():
            try:
                config = cls.from_file(base_config_path)
                config.environment = env_name
            except Exception as e:
                logger.warning(f"Failed to load base config: {e}")
        
        # Apply environment-specific overrides
        env_config_path = Path(f'config/rover_config_{env_name}.json')
        if env_config_path.exists():
            try:
                env_config = cls.from_file(env_config_path)
                config = cls._merge_configs(config, env_config)
            except Exception as e:
                logger.warning(f"Failed to load environment config: {e}")
        
        # Apply environment variable overrides
        config = cls._apply_env_overrides(config)
        
        return config
    
    @staticmethod
    def _merge_configs(base: 'RoverConfig', override: 'RoverConfig') -> 'RoverConfig':
        """
        Merge two configurations, with override taking precedence
        
        Args:
            base: Base configuration
            override: Override configuration
            
        Returns:
            Merged configuration
        """
        base_dict = asdict(base)
        override_dict = asdict(override)
        
        def deep_merge(base_dict: dict, override_dict: dict) -> dict:
            result = base_dict.copy()
            for key, value in override_dict.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        
        merged_dict = deep_merge(base_dict, override_dict)
        return RoverConfig.from_dict(merged_dict)
    
    @staticmethod
    def _apply_env_overrides(config: 'RoverConfig') -> 'RoverConfig':
        """
        Apply environment variable overrides to configuration
        
        Environment variables should be prefixed with ROVER_ and use double
        underscores to separate nested keys (e.g., ROVER_CAMERA__PORT=8080)
        
        Args:
            config: Base configuration
            
        Returns:
            Configuration with environment overrides applied
        """
        config_dict = asdict(config)
        
        for env_key, env_value in os.environ.items():
            if not env_key.startswith('ROVER_'):
                continue
            
            # Remove ROVER_ prefix and convert to lowercase
            key_path = env_key[6:].lower().split('__')
            
            # Navigate to the correct nested dictionary
            current_dict = config_dict
            for key in key_path[:-1]:
                if key in current_dict and isinstance(current_dict[key], dict):
                    current_dict = current_dict[key]
                else:
                    break
            else:
                # Set the value, converting type if necessary
                final_key = key_path[-1]
                if final_key in current_dict:
                    original_type = type(current_dict[final_key])
                    try:
                        if original_type == bool:
                            current_dict[final_key] = env_value.lower() in ('true', '1', 'yes', 'on')
                        elif original_type == int:
                            current_dict[final_key] = int(env_value)
                        elif original_type == float:
                            current_dict[final_key] = float(env_value)
                        else:
                            current_dict[final_key] = env_value
                    except ValueError:
                        logger.warning(f"Failed to convert environment variable {env_key}={env_value}")
        
        return RoverConfig.from_dict(config_dict)
    
    def validate(self) -> bool:
        """
        Validate configuration values
        
        Returns:
            True if configuration is valid, False otherwise
        """
        errors = []
        
        # Validate camera configuration
        if self.camera.port < 1 or self.camera.port > 65535:
            errors.append("Camera port must be between 1 and 65535")
        
        if self.camera.resolution_width < 1 or self.camera.resolution_height < 1:
            errors.append("Camera resolution must be positive")
        
        if self.camera.framerate < 1 or self.camera.framerate > 60:
            errors.append("Camera framerate must be between 1 and 60")
        
        # Validate control configuration
        if self.control.max_speed < 1 or self.control.max_speed > 100:
            errors.append("Max speed must be between 1 and 100")
        
        if self.control.steering_range < 1 or self.control.steering_range > 90:
            errors.append("Steering range must be between 1 and 90 degrees")
        
        # Validate battery configuration
        if self.battery.check_interval < 1:
            errors.append("Battery check interval must be positive")
        
        if self.battery.critical_voltage_threshold >= self.battery.low_voltage_threshold:
            errors.append("Critical voltage threshold must be lower than low voltage threshold")
        
        # Validate logging configuration
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level.upper() not in valid_log_levels:
            errors.append(f"Log level must be one of: {valid_log_levels}")
        
        # Validate network configuration
        if self.network.ssh_port < 1 or self.network.ssh_port > 65535:
            errors.append("SSH port must be between 1 and 65535")
        
        if self.network.web_interface_port < 1 or self.network.web_interface_port > 65535:
            errors.append("Web interface port must be between 1 and 65535")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration validation error: {error}")
            return False
        
        return True
    
    def to_file(self, config_path: Union[str, Path], format: str = 'json') -> None:
        """
        Save configuration to file
        
        Args:
            config_path: Path to save configuration
            format: File format ('json' or 'yaml')
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_dict = asdict(self)
        
        with open(config_path, 'w') as f:
            if format.lower() == 'yaml':
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            else:
                json.dump(config_dict, f, indent=2)
    
    def get_log_level(self) -> int:
        """Get numeric log level for Python logging"""
        return getattr(logging, self.logging.level.upper(), logging.INFO)
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() in ['development', 'dev']
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() in ['production', 'prod']


# Global configuration instance
_config_instance: Optional[RoverConfig] = None


def get_config() -> RoverConfig:
    """
    Get the global configuration instance
    
    Returns:
        RoverConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = RoverConfig.from_environment()
    return _config_instance


def set_config(config: RoverConfig) -> None:
    """
    Set the global configuration instance
    
    Args:
        config: RoverConfig instance to set as global
    """
    global _config_instance
    _config_instance = config


def reload_config(env_name: str = None) -> RoverConfig:
    """
    Reload configuration from files and environment
    
    Args:
        env_name: Environment name to load
        
    Returns:
        Reloaded RoverConfig instance
    """
    global _config_instance
    _config_instance = RoverConfig.from_environment(env_name)
    return _config_instance