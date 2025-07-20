"""
YOLO Detection Engine

Core detection processing using optimized YOLO models.
Supports YOLOv5 and YOLOv8 models optimized for Raspberry Pi.
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import numpy as np

try:
    import torch
    import torchvision
    from ultralytics import YOLO
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch or Ultralytics not available. YOLO detection will use mock mode.")

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logging.warning("ONNX Runtime not available. ONNX model support disabled.")

from .models import Detection, BoundingBox, ObjectClass, PerformanceMetrics
from .config import YOLOConfig


class ModelLoadError(Exception):
    """Exception raised when model loading fails."""
    pass


class YOLODetectionEngine:
    """
    Core YOLO detection engine with model loading and inference capabilities.
    
    Supports YOLOv5n and YOLOv8n models optimized for Raspberry Pi with
    error handling and fallback mechanisms.
    """
    
    def __init__(self, config: YOLOConfig):
        """
        Initialize YOLO detection engine.
        
        Args:
            config: YOLO configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.model_type = None  # 'ultralytics', 'onnx', or 'mock'
        self.class_names = []
        self.enabled_class_indices = set()
        self.performance_stats = {
            'total_inferences': 0,
            'total_inference_time': 0.0,
            'last_inference_time': 0.0,
            'model_load_time': 0.0
        }
        
        # Initialize model
        self._load_model()
        self._setup_class_filtering()
    
    def _load_model(self) -> None:
        """
        Load YOLO model with fallback mechanisms.
        
        Tries to load models in the following order:
        1. Specified model path (PyTorch/Ultralytics)
        2. ONNX version if available
        3. Default YOLOv5n model
        4. Mock model for testing
        """
        start_time = time.time()
        
        try:
            # First try to load the specified model
            if self._load_ultralytics_model(self.config.model_path):
                self.performance_stats['model_load_time'] = time.time() - start_time
                return
        except Exception as e:
            self.logger.warning(f"Failed to load primary model {self.config.model_path}: {e}")
        
        # Try fallback models
        fallback_models = [
            "models/yolov5n.pt",
            "models/yolov8n.pt",
            "yolov5n.pt",  # Will download if not present
            "yolov8n.pt"   # Will download if not present
        ]
        
        for model_path in fallback_models:
            try:
                if self._load_ultralytics_model(model_path):
                    self.logger.info(f"Successfully loaded fallback model: {model_path}")
                    self.performance_stats['model_load_time'] = time.time() - start_time
                    return
            except Exception as e:
                self.logger.debug(f"Failed to load fallback model {model_path}: {e}")
        
        # Try ONNX models if available
        if ONNX_AVAILABLE:
            onnx_models = [
                "models/yolov5n.onnx",
                "models/yolov8n.onnx"
            ]
            
            for model_path in onnx_models:
                try:
                    if self._load_onnx_model(model_path):
                        self.logger.info(f"Successfully loaded ONNX model: {model_path}")
                        self.performance_stats['model_load_time'] = time.time() - start_time
                        return
                except Exception as e:
                    self.logger.debug(f"Failed to load ONNX model {model_path}: {e}")
        
        # Final fallback to mock model
        self.logger.warning("All model loading attempts failed. Using mock model for testing.")
        self._load_mock_model()
        self.performance_stats['model_load_time'] = time.time() - start_time
    
    def _load_ultralytics_model(self, model_path: str) -> bool:
        """
        Load Ultralytics YOLO model.
        
        Args:
            model_path: Path to the model file
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        if not TORCH_AVAILABLE:
            return False
        
        try:
            # Check if model file exists (for local files)
            if model_path.startswith(('models/', './', '/')):
                if not Path(model_path).exists():
                    return False
            
            # Load model
            self.model = YOLO(model_path)
            
            # Configure device
            if self.config.device == 'auto':
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
            else:
                device = self.config.device
            
            # Move model to device
            self.model.to(device)
            
            # Get class names
            if hasattr(self.model, 'names'):
                self.class_names = list(self.model.names.values())
            else:
                # Default COCO class names
                self.class_names = self._get_default_class_names()
            
            self.model_type = 'ultralytics'
            self.logger.info(f"Successfully loaded Ultralytics model: {model_path} on {device}")
            return True
            
        except Exception as e:
            self.logger.debug(f"Failed to load Ultralytics model {model_path}: {e}")
            return False
    
    def _load_onnx_model(self, model_path: str) -> bool:
        """
        Load ONNX model.
        
        Args:
            model_path: Path to the ONNX model file
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        if not ONNX_AVAILABLE or not Path(model_path).exists():
            return False
        
        try:
            # Create ONNX runtime session
            providers = ['CPUExecutionProvider']
            if self.config.device == 'cuda' and 'CUDAExecutionProvider' in ort.get_available_providers():
                providers.insert(0, 'CUDAExecutionProvider')
            
            self.model = ort.InferenceSession(model_path, providers=providers)
            self.class_names = self._get_default_class_names()
            self.model_type = 'onnx'
            self.logger.info(f"Successfully loaded ONNX model: {model_path}")
            return True
            
        except Exception as e:
            self.logger.debug(f"Failed to load ONNX model {model_path}: {e}")
            return False
    
    def _load_mock_model(self) -> None:
        """Load mock model for testing purposes."""
        self.model = None
        self.model_type = 'mock'
        self.class_names = self._get_default_class_names()
        self.logger.info("Loaded mock model for testing")
    
    def _get_default_class_names(self) -> List[str]:
        """Get default COCO class names."""
        return [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
            'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
            'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
            'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
            'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
            'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
            'toothbrush'
        ]
    
    def _setup_class_filtering(self) -> None:
        """Setup class filtering based on enabled classes configuration."""
        if not self.config.enabled_classes:
            # Enable all classes if none specified
            self.enabled_class_indices = set(range(len(self.class_names)))
        else:
            # Map enabled class names to indices
            self.enabled_class_indices = set()
            for class_name in self.config.enabled_classes:
                try:
                    class_idx = self.class_names.index(class_name)
                    self.enabled_class_indices.add(class_idx)
                except ValueError:
                    self.logger.warning(f"Class '{class_name}' not found in model classes")
        
        enabled_names = [self.class_names[i] for i in self.enabled_class_indices]
        self.logger.info(f"Enabled detection classes: {enabled_names}")
    
    def detect_objects(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect objects in the given frame.
        
        Args:
            frame: Input frame as numpy array (BGR format)
            
        Returns:
            List of Detection objects
        """
        if self.model is None and self.model_type != 'mock':
            self.logger.error("Model not loaded. Cannot perform detection.")
            return []
        
        start_time = time.time()
        
        try:
            if self.model_type == 'ultralytics':
                detections = self._detect_ultralytics(frame)
            elif self.model_type == 'onnx':
                detections = self._detect_onnx(frame)
            else:  # mock
                detections = self._detect_mock(frame)
            
            # Update performance statistics
            inference_time = time.time() - start_time
            self.performance_stats['total_inferences'] += 1
            self.performance_stats['total_inference_time'] += inference_time
            self.performance_stats['last_inference_time'] = inference_time
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Detection failed: {e}")
            return []
    
    def _detect_ultralytics(self, frame: np.ndarray) -> List[Detection]:
        """Perform detection using Ultralytics model."""
        # Preprocess frame for YOLO input
        processed_frame = self._preprocess_frame(frame)
        
        # Run inference
        results = self.model(processed_frame, conf=self.config.confidence_threshold, 
                           iou=self.config.nms_threshold, verbose=False)
        
        detections = []
        frame_id = int(time.time() * 1000)  # Use timestamp as frame ID
        timestamp = time.time()
        
        for result in results:
            if result.boxes is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                confidences = result.boxes.conf.cpu().numpy()
                class_ids = result.boxes.cls.cpu().numpy().astype(int)
                
                # Apply additional confidence filtering
                valid_indices = confidences >= self.config.confidence_threshold
                boxes = boxes[valid_indices]
                confidences = confidences[valid_indices]
                class_ids = class_ids[valid_indices]
                
                # Apply NMS if needed (Ultralytics usually handles this, but we can add custom NMS)
                if len(boxes) > 0:
                    nms_indices = self._apply_nms(boxes, confidences, self.config.nms_threshold)
                    boxes = boxes[nms_indices]
                    confidences = confidences[nms_indices]
                    class_ids = class_ids[nms_indices]
                
                # Scale boxes back to original frame size if preprocessing changed dimensions
                original_height, original_width = frame.shape[:2]
                processed_height, processed_width = processed_frame.shape[:2]
                
                if (original_height != processed_height) or (original_width != processed_width):
                    boxes = self._scale_boxes(boxes, 
                                            (processed_width, processed_height),
                                            (original_width, original_height))
                
                for box, conf, class_id in zip(boxes, confidences, class_ids):
                    # Filter by enabled classes
                    if class_id not in self.enabled_class_indices:
                        continue
                    
                    # Create detection object
                    class_name = self.class_names[class_id]
                    try:
                        object_class = ObjectClass(class_name)
                    except ValueError:
                        # Skip unknown classes
                        continue
                    
                    bbox = BoundingBox(
                        x1=int(box[0]),
                        y1=int(box[1]),
                        x2=int(box[2]),
                        y2=int(box[3])
                    )
                    
                    detection = Detection(
                        object_class=object_class,
                        confidence=float(conf),
                        bbox=bbox,
                        timestamp=timestamp,
                        frame_id=frame_id
                    )
                    
                    detections.append(detection)
        
        return detections
    
    def _detect_onnx(self, frame: np.ndarray) -> List[Detection]:
        """Perform detection using ONNX model."""
        # This is a simplified ONNX implementation
        # In a full implementation, you would need to handle preprocessing,
        # postprocessing, and NMS manually
        self.logger.warning("ONNX detection not fully implemented. Using mock detection.")
        return self._detect_mock(frame)
    
    def _detect_mock(self, frame: np.ndarray) -> List[Detection]:
        """Generate mock detections for testing."""
        detections = []
        frame_id = int(time.time() * 1000)
        timestamp = time.time()
        
        # Generate a few mock detections
        height, width = frame.shape[:2]
        
        # Mock person detection
        if 'person' in self.config.enabled_classes:
            bbox = BoundingBox(
                x1=width // 4,
                y1=height // 4,
                x2=width // 2,
                y2=3 * height // 4
            )
            
            detection = Detection(
                object_class=ObjectClass.PERSON,
                confidence=0.85,
                bbox=bbox,
                timestamp=timestamp,
                frame_id=frame_id
            )
            detections.append(detection)
        
        # Mock dog detection
        if 'dog' in self.config.enabled_classes:
            bbox = BoundingBox(
                x1=width // 2,
                y1=height // 2,
                x2=3 * width // 4,
                y2=3 * height // 4
            )
            
            detection = Detection(
                object_class=ObjectClass.DOG,
                confidence=0.75,
                bbox=bbox,
                timestamp=timestamp,
                frame_id=frame_id
            )
            detections.append(detection)
        
        return detections
    
    def set_confidence_threshold(self, threshold: float) -> None:
        """
        Set confidence threshold for detections.
        
        Args:
            threshold: Confidence threshold (0.0 to 1.0)
        """
        if 0.0 <= threshold <= 1.0:
            self.config.confidence_threshold = threshold
            self.logger.info(f"Confidence threshold set to {threshold}")
        else:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
    
    def set_enabled_classes(self, classes: List[str]) -> None:
        """
        Set enabled object classes for detection.
        
        Args:
            classes: List of class names to enable
            
        Raises:
            ValueError: If any class names are invalid for the current model
        """
        # Validate class names against model capabilities
        invalid_classes = self.validate_class_names(classes)
        if invalid_classes:
            self.logger.warning(f"Invalid class names will be ignored: {invalid_classes}")
        
        # Filter out invalid classes
        valid_classes = [cls for cls in classes if cls in self.class_names]
        
        if not valid_classes:
            raise ValueError("No valid class names provided")
        
        self.config.enabled_classes = valid_classes
        self._setup_class_filtering()
        self.logger.info(f"Enabled classes updated: {valid_classes}")
        
        if invalid_classes:
            self.logger.info(f"Available classes: {self.get_available_classes()}")
    
    def validate_class_names(self, class_names: List[str]) -> List[str]:
        """
        Validate class names against model capabilities.
        
        Args:
            class_names: List of class names to validate
            
        Returns:
            List of invalid class names
        """
        if not class_names:
            return []
        
        invalid_classes = []
        for class_name in class_names:
            if class_name not in self.class_names:
                invalid_classes.append(class_name)
        
        return invalid_classes
    
    def get_available_classes(self) -> List[str]:
        """
        Get list of all available object classes for the current model.
        
        Returns:
            List of available class names
        """
        return self.class_names.copy()
    
    def get_enabled_classes(self) -> List[str]:
        """
        Get list of currently enabled object classes.
        
        Returns:
            List of enabled class names
        """
        return self.config.enabled_classes.copy() if self.config.enabled_classes else []
    
    def is_class_enabled(self, class_name: str) -> bool:
        """
        Check if a specific object class is enabled for detection.
        
        Args:
            class_name: Name of the class to check
            
        Returns:
            True if class is enabled, False otherwise
        """
        if not self.config.enabled_classes:
            return True  # All classes enabled if none specified
        
        return class_name in self.config.enabled_classes
    
    def enable_class(self, class_name: str) -> bool:
        """
        Enable a specific object class for detection.
        
        Args:
            class_name: Name of the class to enable
            
        Returns:
            True if class was enabled successfully, False if invalid
        """
        if class_name not in self.class_names:
            self.logger.warning(f"Cannot enable invalid class: {class_name}")
            return False
        
        if not self.config.enabled_classes:
            self.config.enabled_classes = []
        
        if class_name not in self.config.enabled_classes:
            self.config.enabled_classes.append(class_name)
            self._setup_class_filtering()
            self.logger.info(f"Enabled class: {class_name}")
        
        return True
    
    def disable_class(self, class_name: str) -> bool:
        """
        Disable a specific object class for detection.
        
        Args:
            class_name: Name of the class to disable
            
        Returns:
            True if class was disabled successfully, False if not found
        """
        if not self.config.enabled_classes:
            # If no classes specified, all are enabled - create list without this class
            self.config.enabled_classes = [cls for cls in self.class_names if cls != class_name]
        elif class_name in self.config.enabled_classes:
            self.config.enabled_classes.remove(class_name)
        else:
            return False
        
        self._setup_class_filtering()
        self.logger.info(f"Disabled class: {class_name}")
        return True
    
    def get_class_statistics(self) -> Dict[str, int]:
        """
        Get detection statistics by object class.
        
        Returns:
            Dictionary mapping class names to detection counts
        """
        # This would be implemented with actual detection tracking
        # For now, return empty stats
        return {class_name: 0 for class_name in self.get_enabled_classes()}
    
    def get_performance_stats(self) -> Dict[str, float]:
        """
        Get performance statistics.
        
        Returns:
            Dictionary containing performance metrics
        """
        stats = self.performance_stats.copy()
        
        # Calculate average inference time
        if stats['total_inferences'] > 0:
            stats['avg_inference_time'] = stats['total_inference_time'] / stats['total_inferences']
            stats['avg_fps'] = 1.0 / stats['avg_inference_time'] if stats['avg_inference_time'] > 0 else 0.0
        else:
            stats['avg_inference_time'] = 0.0
            stats['avg_fps'] = 0.0
        
        return stats
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary containing model information
        """
        return {
            'model_type': self.model_type,
            'model_path': self.config.model_path,
            'device': self.config.device,
            'class_count': len(self.class_names),
            'enabled_classes': self.config.enabled_classes,
            'confidence_threshold': self.config.confidence_threshold,
            'nms_threshold': self.config.nms_threshold,
            'is_loaded': self.model is not None or self.model_type == 'mock'
        }
    
    def reload_model(self) -> bool:
        """
        Reload the model (useful for model updates).
        
        Returns:
            True if reload successful, False otherwise
        """
        try:
            self.logger.info("Reloading YOLO model...")
            old_model_type = self.model_type
            self.model = None
            self.model_type = None
            
            self._load_model()
            self._setup_class_filtering()
            
            self.logger.info(f"Model reloaded successfully (was: {old_model_type}, now: {self.model_type})")
            return True
            
        except Exception as e:
            self.logger.error(f"Model reload failed: {e}")
            return False
    
    def is_ready(self) -> bool:
        """
        Check if the detection engine is ready for inference.
        
        Returns:
            True if ready, False otherwise
        """
        return self.model is not None or self.model_type == 'mock'
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for YOLO input format.
        
        Args:
            frame: Input frame (BGR format)
            
        Returns:
            Preprocessed frame ready for YOLO inference
        """
        # Get target input size
        target_height, target_width = self.config.input_size
        
        # Resize frame while maintaining aspect ratio
        height, width = frame.shape[:2]
        
        # Calculate scaling factor
        scale = min(target_width / width, target_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Resize frame
        if TORCH_AVAILABLE:
            import cv2
            resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        else:
            # Fallback resize using numpy (basic nearest neighbor)
            resized_frame = self._resize_frame_numpy(frame, (new_width, new_height))
        
        # Create padded frame with target size
        processed_frame = np.full((target_height, target_width, 3), 114, dtype=np.uint8)  # Gray padding
        
        # Calculate padding offsets
        y_offset = (target_height - new_height) // 2
        x_offset = (target_width - new_width) // 2
        
        # Place resized frame in center
        processed_frame[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = resized_frame
        
        return processed_frame
    
    def _resize_frame_numpy(self, frame: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
        """
        Basic frame resizing using numpy (fallback when OpenCV not available).
        
        Args:
            frame: Input frame
            target_size: (width, height) target size
            
        Returns:
            Resized frame
        """
        target_width, target_height = target_size
        height, width = frame.shape[:2]
        
        # Simple nearest neighbor resizing
        y_indices = np.round(np.linspace(0, height - 1, target_height)).astype(int)
        x_indices = np.round(np.linspace(0, width - 1, target_width)).astype(int)
        
        # Create meshgrid for indexing
        y_grid, x_grid = np.meshgrid(y_indices, x_indices, indexing='ij')
        
        # Resize frame
        resized_frame = frame[y_grid, x_grid]
        
        return resized_frame
    
    def _apply_nms(self, boxes: np.ndarray, confidences: np.ndarray, iou_threshold: float) -> np.ndarray:
        """
        Apply Non-Maximum Suppression to remove duplicate detections.
        
        Args:
            boxes: Array of bounding boxes (N, 4) in format [x1, y1, x2, y2]
            confidences: Array of confidence scores (N,)
            iou_threshold: IoU threshold for NMS
            
        Returns:
            Array of indices to keep after NMS
        """
        if len(boxes) == 0:
            return np.array([], dtype=int)
        
        # Sort by confidence (descending)
        sorted_indices = np.argsort(confidences)[::-1]
        
        keep_indices = []
        
        while len(sorted_indices) > 0:
            # Take the box with highest confidence
            current_idx = sorted_indices[0]
            keep_indices.append(current_idx)
            
            if len(sorted_indices) == 1:
                break
            
            # Calculate IoU with remaining boxes
            current_box = boxes[current_idx]
            remaining_boxes = boxes[sorted_indices[1:]]
            
            ious = self._calculate_iou(current_box, remaining_boxes)
            
            # Keep boxes with IoU below threshold
            keep_mask = ious < iou_threshold
            sorted_indices = sorted_indices[1:][keep_mask]
        
        return np.array(keep_indices, dtype=int)
    
    def _calculate_iou(self, box1: np.ndarray, boxes: np.ndarray) -> np.ndarray:
        """
        Calculate Intersection over Union (IoU) between one box and multiple boxes.
        
        Args:
            box1: Single bounding box [x1, y1, x2, y2]
            boxes: Multiple bounding boxes (N, 4) in format [x1, y1, x2, y2]
            
        Returns:
            Array of IoU values
        """
        # Calculate intersection coordinates
        x1_inter = np.maximum(box1[0], boxes[:, 0])
        y1_inter = np.maximum(box1[1], boxes[:, 1])
        x2_inter = np.minimum(box1[2], boxes[:, 2])
        y2_inter = np.minimum(box1[3], boxes[:, 3])
        
        # Calculate intersection area
        inter_width = np.maximum(0, x2_inter - x1_inter)
        inter_height = np.maximum(0, y2_inter - y1_inter)
        intersection = inter_width * inter_height
        
        # Calculate areas
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        boxes_area = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        
        # Calculate union
        union = box1_area + boxes_area - intersection
        
        # Calculate IoU (avoid division by zero)
        iou = np.divide(intersection, union, out=np.zeros_like(intersection, dtype=np.float64), where=union != 0)
        
        return iou
    
    def _scale_boxes(self, boxes: np.ndarray, from_size: Tuple[int, int], to_size: Tuple[int, int]) -> np.ndarray:
        """
        Scale bounding boxes from one image size to another.
        
        Args:
            boxes: Bounding boxes (N, 4) in format [x1, y1, x2, y2]
            from_size: Original image size (width, height)
            to_size: Target image size (width, height)
            
        Returns:
            Scaled bounding boxes
        """
        from_width, from_height = from_size
        to_width, to_height = to_size
        
        # Calculate scaling factors
        x_scale = to_width / from_width
        y_scale = to_height / from_height
        
        # Scale boxes
        scaled_boxes = boxes.copy().astype(np.float64)
        scaled_boxes[:, [0, 2]] *= x_scale  # x1, x2
        scaled_boxes[:, [1, 3]] *= y_scale  # y1, y2
        
        # Ensure boxes are within image bounds
        scaled_boxes[:, [0, 2]] = np.clip(scaled_boxes[:, [0, 2]], 0, to_width)
        scaled_boxes[:, [1, 3]] = np.clip(scaled_boxes[:, [1, 3]], 0, to_height)
        
        return scaled_boxes