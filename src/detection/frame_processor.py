"""
Frame Processing Pipeline

Efficient capture, preprocessing, and distribution of video frames for YOLO detection.
Handles frame preprocessing, normalization, and format conversion.
"""

import logging
import time
from typing import Tuple, Optional, Dict, Any
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV not available. Using basic frame processing.")


class FrameProcessor:
    """
    Frame processor for YOLO detection pipeline.
    
    Handles frame preprocessing including resizing, normalization,
    and format conversion for optimal YOLO inference performance.
    """
    
    def __init__(self, input_size: Tuple[int, int] = (640, 640)):
        """
        Initialize frame processor.
        
        Args:
            input_size: Target input size for YOLO model (width, height)
        """
        self.input_size = input_size
        self.logger = logging.getLogger(__name__)
        self.processing_stats = {
            'total_frames': 0,
            'total_processing_time': 0.0,
            'last_processing_time': 0.0
        }
        
        self.logger.info(f"FrameProcessor initialized with input size: {input_size}")
    
    def preprocess_frame(self, frame: np.ndarray, normalize: bool = True) -> Dict[str, Any]:
        """
        Preprocess frame for YOLO detection.
        
        Args:
            frame: Input frame (BGR format)
            normalize: Whether to normalize pixel values to [0, 1]
            
        Returns:
            Dictionary containing processed frame and metadata
        """
        start_time = time.time()
        
        try:
            # Store original dimensions
            original_height, original_width = frame.shape[:2]
            
            # Resize frame while maintaining aspect ratio
            processed_frame, scale_info = self._resize_with_padding(frame)
            
            # Convert color space if needed (BGR to RGB for some models)
            if processed_frame.shape[2] == 3:
                processed_frame = self._convert_color_space(processed_frame)
            
            # Normalize pixel values if requested
            if normalize:
                processed_frame = self._normalize_frame(processed_frame)
            
            # Update processing statistics
            processing_time = time.time() - start_time
            self.processing_stats['total_frames'] += 1
            self.processing_stats['total_processing_time'] += processing_time
            self.processing_stats['last_processing_time'] = processing_time
            
            return {
                'frame': processed_frame,
                'original_size': (original_width, original_height),
                'processed_size': self.input_size,
                'scale_info': scale_info,
                'processing_time': processing_time,
                'normalized': normalize
            }
            
        except Exception as e:
            self.logger.error(f"Frame preprocessing failed: {e}")
            return {
                'frame': frame,
                'original_size': frame.shape[1::-1],  # (width, height)
                'processed_size': frame.shape[1::-1],
                'scale_info': {'scale': 1.0, 'pad_x': 0, 'pad_y': 0},
                'processing_time': time.time() - start_time,
                'normalized': False,
                'error': str(e)
            }
    
    def _resize_with_padding(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Resize frame while maintaining aspect ratio using padding.
        
        Args:
            frame: Input frame
            
        Returns:
            Tuple of (resized_frame, scale_info)
        """
        target_width, target_height = self.input_size
        height, width = frame.shape[:2]
        
        # Calculate scaling factor to maintain aspect ratio
        scale = min(target_width / width, target_height / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Resize frame
        if CV2_AVAILABLE:
            resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        else:
            resized_frame = self._resize_numpy(frame, (new_width, new_height))
        
        # Create padded frame with target size
        padded_frame = np.full((target_height, target_width, frame.shape[2]), 114, dtype=frame.dtype)
        
        # Calculate padding offsets (center the image)
        pad_y = (target_height - new_height) // 2
        pad_x = (target_width - new_width) // 2
        
        # Place resized frame in center of padded frame
        padded_frame[pad_y:pad_y + new_height, pad_x:pad_x + new_width] = resized_frame
        
        scale_info = {
            'scale': scale,
            'pad_x': pad_x,
            'pad_y': pad_y,
            'new_width': new_width,
            'new_height': new_height
        }
        
        return padded_frame, scale_info
    
    def _resize_numpy(self, frame: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
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
        
        # Create coordinate arrays for nearest neighbor interpolation
        y_indices = np.round(np.linspace(0, height - 1, target_height)).astype(int)
        x_indices = np.round(np.linspace(0, width - 1, target_width)).astype(int)
        
        # Create meshgrid for indexing
        y_grid, x_grid = np.meshgrid(y_indices, x_indices, indexing='ij')
        
        # Resize frame using advanced indexing
        resized_frame = frame[y_grid, x_grid]
        
        return resized_frame
    
    def _convert_color_space(self, frame: np.ndarray, target_format: str = 'RGB') -> np.ndarray:
        """
        Convert frame color space.
        
        Args:
            frame: Input frame (assumed BGR)
            target_format: Target color format ('RGB' or 'BGR')
            
        Returns:
            Converted frame
        """
        if target_format == 'RGB':
            if CV2_AVAILABLE:
                return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                # Manual BGR to RGB conversion
                return frame[:, :, ::-1]
        
        return frame  # Return as-is for BGR or unknown formats
    
    def _normalize_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Normalize frame pixel values to [0, 1] range.
        
        Args:
            frame: Input frame with pixel values in [0, 255]
            
        Returns:
            Normalized frame with pixel values in [0, 1]
        """
        return frame.astype(np.float32) / 255.0
    
    def postprocess_detections(self, detections: np.ndarray, scale_info: Dict[str, float], 
                             original_size: Tuple[int, int]) -> np.ndarray:
        """
        Postprocess detection results to original frame coordinates.
        
        Args:
            detections: Detection results (N, 6) [x1, y1, x2, y2, conf, class]
            scale_info: Scaling information from preprocessing
            original_size: Original frame size (width, height)
            
        Returns:
            Detections scaled back to original frame coordinates
        """
        if len(detections) == 0:
            return detections
        
        # Extract scaling parameters
        scale = scale_info['scale']
        pad_x = scale_info['pad_x']
        pad_y = scale_info['pad_y']
        
        # Copy detections to avoid modifying original
        scaled_detections = detections.copy()
        
        # Remove padding offset
        scaled_detections[:, [0, 2]] -= pad_x  # x coordinates
        scaled_detections[:, [1, 3]] -= pad_y  # y coordinates
        
        # Scale back to original size
        scaled_detections[:, [0, 2]] /= scale  # x coordinates
        scaled_detections[:, [1, 3]] /= scale  # y coordinates
        
        # Clip to original image bounds
        original_width, original_height = original_size
        scaled_detections[:, [0, 2]] = np.clip(scaled_detections[:, [0, 2]], 0, original_width)
        scaled_detections[:, [1, 3]] = np.clip(scaled_detections[:, [1, 3]], 0, original_height)
        
        return scaled_detections
    
    def get_processing_stats(self) -> Dict[str, float]:
        """
        Get frame processing statistics.
        
        Returns:
            Dictionary containing processing metrics
        """
        stats = self.processing_stats.copy()
        
        if stats['total_frames'] > 0:
            stats['avg_processing_time'] = stats['total_processing_time'] / stats['total_frames']
            stats['avg_fps'] = 1.0 / stats['avg_processing_time'] if stats['avg_processing_time'] > 0 else 0.0
        else:
            stats['avg_processing_time'] = 0.0
            stats['avg_fps'] = 0.0
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self.processing_stats = {
            'total_frames': 0,
            'total_processing_time': 0.0,
            'last_processing_time': 0.0
        }
        self.logger.info("Processing statistics reset")
    
    def set_input_size(self, input_size: Tuple[int, int]) -> None:
        """
        Update input size for frame processing.
        
        Args:
            input_size: New target input size (width, height)
        """
        self.input_size = input_size
        self.logger.info(f"Input size updated to: {input_size}")
    
    def validate_frame(self, frame: np.ndarray) -> bool:
        """
        Validate input frame format and dimensions.
        
        Args:
            frame: Input frame to validate
            
        Returns:
            True if frame is valid, False otherwise
        """
        if frame is None:
            return False
        
        if not isinstance(frame, np.ndarray):
            return False
        
        if len(frame.shape) != 3:
            return False
        
        if frame.shape[2] not in [1, 3, 4]:  # Grayscale, RGB/BGR, or RGBA
            return False
        
        if frame.size == 0:
            return False
        
        return True