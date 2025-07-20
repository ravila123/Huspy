"""
YOLO Object Detection Module

This module provides YOLO-based object detection capabilities for the Blue Rover project.
It includes the detection engine, frame processing, API services, and configuration management.
"""

__version__ = "1.0.0"
__author__ = "Blue Rover Team"

# Data models (available now)
from .models import Detection, DetectionFrame, BoundingBox, ObjectClass, PerformanceMetrics, AlertEvent

# Configuration (available now)
from .config import YOLOConfig, AlertConfig, PerformanceConfig, YOLODetectionConfig

# Core detection components (will be implemented in future tasks)
# from .yolo_engine import YOLODetectionEngine
# from .frame_processor import FrameProcessor
# from .detection_service import YOLODetectionService

__all__ = [
    # Data models
    "Detection",
    "DetectionFrame",
    "BoundingBox",
    "ObjectClass",
    "PerformanceMetrics",
    "AlertEvent",
    # Configuration
    "YOLOConfig",
    "AlertConfig",
    "PerformanceConfig",
    "YOLODetectionConfig"
    # Core components (to be added in future tasks)
    # "YOLODetectionEngine",
    # "FrameProcessor", 
    # "YOLODetectionService",
]