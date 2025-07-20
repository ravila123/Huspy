"""
Configuration management for YOLO object detection system.

This module defines configuration data classes and provides utilities for
loading, validating, and managing YOLO detection settings.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import json
import os
from pathlib import Path


@dataclass
class YOLOConfig:
    """Configuration for YOLO detection engine."""
    enabled: bool = True
    model_path: str = "models/yolov5n.pt"
    confidence_threshold: float = 0.5
    nms_threshold: float = 0.4
    input_size: Tuple[int, int] = (640, 640)
    target_fps: int = 10
    enabled_classes: Optional[List[str]] = None
    device: str = "cpu"  # cpu, cuda, mps
    
    def __post_init__(self):
        """Validate configuration values after initialization."""
        if self.confidence_threshold < 0.0 or self.confidence_threshold > 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        if self.nms_threshold < 0.0 or self.nms_threshold > 1.0:
            raise ValueError("nms_threshold must be between 0.0 and 1.0")
        if self.target_fps <= 0:
            raise ValueError("target_fps must be positive")
        if self.enabled_classes is None:
            self.enabled_classes = ["person", "car", "bicycle", "dog", "cat"]


@dataclass
class AlertConfig:
    """Configuration for alert system."""
    enabled: bool = True
    alert_classes: Optional[List[str]] = None
    confidence_threshold: float = 0.7
    rate_limit_seconds: int = 30
    max_alerts_per_minute: int = 10
    
    def __post_init__(self):
        """Validate configuration values after initialization."""
        if self.confidence_threshold < 0.0 or self.confidence_threshold > 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        if self.rate_limit_seconds < 0:
            raise ValueError("rate_limit_seconds must be non-negative")
        if self.alert_classes is None:
            self.alert_classes = ["person", "dog"]


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""
    max_cpu_usage: int = 80
    adaptive_fps: bool = True
    use_hardware_acceleration: bool = True
    max_memory_mb: int = 1024
    frame_buffer_size: int = 5
    processing_threads: int = 2
    
    def __post_init__(self):
        """Validate configuration values after initialization."""
        if self.max_cpu_usage <= 0 or self.max_cpu_usage > 100:
            raise ValueError("max_cpu_usage must be between 1 and 100")
        if self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        if self.frame_buffer_size <= 0:
            raise ValueError("frame_buffer_size must be positive")
        if self.processing_threads <= 0:
            raise ValueError("processing_threads must be positive")


@dataclass
class YOLODetectionConfig:
    """Complete configuration for YOLO detection system."""
    yolo: YOLOConfig = field(default_factory=YOLOConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'YOLODetectionConfig':
        """Create configuration from dictionary."""
        yolo_config = YOLOConfig(**config_dict.get('yolo', {}))
        alert_config = AlertConfig(**config_dict.get('alerts', {}))
        performance_config = PerformanceConfig(**config_dict.get('performance', {}))
        
        return cls(
            yolo=yolo_config,
            alerts=alert_config,
            performance=performance_config
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'yolo': {
                'enabled': self.yolo.enabled,
                'model_path': self.yolo.model_path,
                'confidence_threshold': self.yolo.confidence_threshold,
                'nms_threshold': self.yolo.nms_threshold,
                'input_size': list(self.yolo.input_size),
                'target_fps': self.yolo.target_fps,
                'enabled_classes': self.yolo.enabled_classes,
                'device': self.yolo.device
            },
            'alerts': {
                'enabled': self.alerts.enabled,
                'alert_classes': self.alerts.alert_classes,
                'confidence_threshold': self.alerts.confidence_threshold,
                'rate_limit_seconds': self.alerts.rate_limit_seconds,
                'max_alerts_per_minute': self.alerts.max_alerts_per_minute
            },
            'performance': {
                'max_cpu_usage': self.performance.max_cpu_usage,
                'adaptive_fps': self.performance.adaptive_fps,
                'use_hardware_acceleration': self.performance.use_hardware_acceleration,
                'max_memory_mb': self.performance.max_memory_mb,
                'frame_buffer_size': self.performance.frame_buffer_size,
                'processing_threads': self.performance.processing_threads
            }
        }
    
    @classmethod
    def load_from_file(cls, config_path: str) -> 'YOLODetectionConfig':
        """Load configuration from JSON file."""
        if not os.path.exists(config_path):
            return cls()  # Return default configuration
        
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
            return cls.from_dict(config_dict.get('yolo_detection', {}))
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Invalid configuration file: {e}")
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to JSON file."""
        # Load existing config if it exists
        existing_config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    existing_config = json.load(f)
            except json.JSONDecodeError:
                pass  # Start with empty config if file is corrupted
        
        # Update with YOLO detection config
        existing_config['yolo_detection'] = self.to_dict()
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(existing_config, f, indent=2)


def get_default_config() -> YOLODetectionConfig:
    """Get default YOLO detection configuration."""
    return YOLODetectionConfig()


def validate_model_path(model_path: str) -> bool:
    """Validate that the model path exists and is accessible."""
    if not model_path:
        return False
    
    path = Path(model_path)
    return path.exists() and path.is_file() and path.suffix in ['.pt', '.onnx', '.engine']


def get_available_classes() -> List[str]:
    """Get list of available object classes for detection."""
    return [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
        "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
        "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
        "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
        "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
        "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
        "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
        "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
        "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
        "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
        "toothbrush"
    ]