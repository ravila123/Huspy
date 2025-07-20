"""
Data models for YOLO object detection system.

This module defines the core data structures used throughout the YOLO detection system,
including detection results, bounding boxes, and performance metrics.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum


class ObjectClass(Enum):
    """Enumeration of supported object classes for detection."""
    PERSON = "person"
    CAR = "car"
    BICYCLE = "bicycle"
    DOG = "dog"
    CAT = "cat"
    MOTORCYCLE = "motorcycle"
    BUS = "bus"
    TRUCK = "truck"
    BIRD = "bird"
    HORSE = "horse"


@dataclass
class BoundingBox:
    """Represents a bounding box around a detected object."""
    x1: int
    y1: int
    x2: int
    y2: int
    
    @property
    def center(self) -> Tuple[int, int]:
        """Calculate the center point of the bounding box."""
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)
    
    @property
    def area(self) -> int:
        """Calculate the area of the bounding box."""
        return (self.x2 - self.x1) * (self.y2 - self.y1)
    
    @property
    def width(self) -> int:
        """Get the width of the bounding box."""
        return self.x2 - self.x1
    
    @property
    def height(self) -> int:
        """Get the height of the bounding box."""
        return self.y2 - self.y1


@dataclass
class Detection:
    """Represents a single object detection result."""
    object_class: ObjectClass
    confidence: float
    bbox: BoundingBox
    timestamp: float
    frame_id: int
    tracking_id: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert detection to dictionary for JSON serialization."""
        return {
            "object_class": self.object_class.value,
            "confidence": self.confidence,
            "bbox": {
                "x1": self.bbox.x1,
                "y1": self.bbox.y1,
                "x2": self.bbox.x2,
                "y2": self.bbox.y2
            },
            "timestamp": self.timestamp,
            "frame_id": self.frame_id,
            "tracking_id": self.tracking_id
        }


@dataclass
class DetectionFrame:
    """Represents detection results for a single frame."""
    detections: List[Detection]
    frame_timestamp: float
    processing_time: float
    frame_size: Tuple[int, int]
    total_objects: int
    
    def to_dict(self) -> Dict:
        """Convert detection frame to dictionary for JSON serialization."""
        return {
            "detections": [d.to_dict() for d in self.detections],
            "frame_timestamp": self.frame_timestamp,
            "processing_time": self.processing_time,
            "frame_size": self.frame_size,
            "total_objects": self.total_objects
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics for the detection system."""
    fps: float
    avg_processing_time: float
    cpu_usage: float
    memory_usage: float
    dropped_frames: int
    total_detections: int
    
    def to_dict(self) -> Dict:
        """Convert performance metrics to dictionary for JSON serialization."""
        return {
            "fps": self.fps,
            "avg_processing_time": self.avg_processing_time,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "dropped_frames": self.dropped_frames,
            "total_detections": self.total_detections
        }


@dataclass
class AlertEvent:
    """Represents an alert triggered by object detection."""
    detection: Detection
    alert_type: str
    message: str
    timestamp: float
    acknowledged: bool = False
    
    def to_dict(self) -> Dict:
        """Convert alert event to dictionary for JSON serialization."""
        return {
            "detection": self.detection.to_dict(),
            "alert_type": self.alert_type,
            "message": self.message,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged
        }