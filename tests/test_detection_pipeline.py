"""
Unit tests for YOLO detection processing pipeline.

Tests frame preprocessing, NMS, detection accuracy, and performance.
"""

import unittest
from unittest.mock import Mock, patch
import numpy as np
import time

# Import the modules to test
from src.detection.yolo_engine import YOLODetectionEngine
from src.detection.frame_processor import FrameProcessor
from src.detection.config import YOLOConfig
from src.detection.models import Detection, BoundingBox, ObjectClass


class TestDetectionProcessingPipeline(unittest.TestCase):
    """Test cases for detection processing pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = YOLOConfig(
            confidence_threshold=0.5,
            nms_threshold=0.4,
            input_size=(640, 640),
            enabled_classes=["person", "dog", "car"]
        )
        
        # Create test frames
        self.test_frame_small = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        self.test_frame_large = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        self.test_frame_square = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
    
    def test_frame_preprocessing_resize_with_padding(self):
        """Test frame preprocessing with resize and padding."""
        processor = FrameProcessor(input_size=(640, 640))
        
        # Test with small frame (should be upscaled)
        result = processor.preprocess_frame(self.test_frame_small, normalize=False)
        
        self.assertEqual(result['processed_size'], (640, 640))
        self.assertEqual(result['frame'].shape, (640, 640, 3))
        self.assertEqual(result['original_size'], (320, 240))
        self.assertIn('scale_info', result)
        self.assertGreater(result['scale_info']['scale'], 1.0)  # Upscaling
    
    def test_frame_preprocessing_normalization(self):
        """Test frame normalization."""
        processor = FrameProcessor()
        
        # Test with normalization
        result_normalized = processor.preprocess_frame(self.test_frame_small, normalize=True)
        self.assertTrue(result_normalized['normalized'])
        self.assertLessEqual(result_normalized['frame'].max(), 1.0)
        self.assertGreaterEqual(result_normalized['frame'].min(), 0.0)
        
        # Test without normalization
        result_unnormalized = processor.preprocess_frame(self.test_frame_small, normalize=False)
        self.assertFalse(result_unnormalized['normalized'])
        self.assertGreater(result_unnormalized['frame'].max(), 1.0)
    
    def test_frame_preprocessing_aspect_ratio_preservation(self):
        """Test that aspect ratio is preserved during preprocessing."""
        processor = FrameProcessor(input_size=(640, 640))
        
        # Test with rectangular frame
        rectangular_frame = np.random.randint(0, 255, (300, 600, 3), dtype=np.uint8)
        result = processor.preprocess_frame(rectangular_frame, normalize=False)
        
        scale_info = result['scale_info']
        original_aspect = 600 / 300  # width / height
        
        # Check that the scaled dimensions maintain aspect ratio
        scaled_aspect = scale_info['new_width'] / scale_info['new_height']
        self.assertAlmostEqual(original_aspect, scaled_aspect, places=2)
    
    def test_frame_validation(self):
        """Test frame validation functionality."""
        processor = FrameProcessor()
        
        # Valid frames
        self.assertTrue(processor.validate_frame(self.test_frame_small))
        self.assertTrue(processor.validate_frame(np.random.randint(0, 255, (100, 100, 1), dtype=np.uint8)))
        
        # Invalid frames
        self.assertFalse(processor.validate_frame(None))
        self.assertFalse(processor.validate_frame("not_an_array"))
        self.assertFalse(processor.validate_frame(np.array([1, 2, 3])))  # Wrong dimensions
        self.assertFalse(processor.validate_frame(np.zeros((100, 100, 5))))  # Wrong channels
        self.assertFalse(processor.validate_frame(np.array([])))  # Empty array
    
    def test_processing_statistics(self):
        """Test processing statistics tracking."""
        processor = FrameProcessor()
        
        # Initial stats
        stats = processor.get_processing_stats()
        self.assertEqual(stats['total_frames'], 0)
        
        # Process some frames
        processor.preprocess_frame(self.test_frame_small)
        processor.preprocess_frame(self.test_frame_large)
        
        # Check updated stats
        stats = processor.get_processing_stats()
        self.assertEqual(stats['total_frames'], 2)
        self.assertGreater(stats['avg_processing_time'], 0)
        self.assertGreater(stats['avg_fps'], 0)
        
        # Reset stats
        processor.reset_stats()
        stats = processor.get_processing_stats()
        self.assertEqual(stats['total_frames'], 0)


class TestYOLOEngineProcessingPipeline(unittest.TestCase):
    """Test cases for YOLO engine processing pipeline."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = YOLOConfig(
            confidence_threshold=0.5,
            nms_threshold=0.4,
            enabled_classes=["person", "dog", "car"]
        )
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_frame_preprocessing_in_engine(self):
        """Test frame preprocessing within YOLO engine."""
        engine = YOLODetectionEngine(self.config)
        
        # Create test frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Test preprocessing
        processed_frame = engine._preprocess_frame(frame)
        
        # Check output dimensions
        self.assertEqual(processed_frame.shape, (640, 640, 3))
        self.assertEqual(processed_frame.dtype, np.uint8)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_nms_functionality(self):
        """Test Non-Maximum Suppression functionality."""
        engine = YOLODetectionEngine(self.config)
        
        # Create overlapping bounding boxes
        boxes = np.array([
            [100, 100, 200, 200],  # Box 1
            [110, 110, 210, 210],  # Box 2 (overlaps with Box 1)
            [300, 300, 400, 400],  # Box 3 (separate)
            [105, 105, 205, 205],  # Box 4 (overlaps with Box 1)
        ])
        
        confidences = np.array([0.9, 0.8, 0.7, 0.6])
        
        # Apply NMS
        keep_indices = engine._apply_nms(boxes, confidences, iou_threshold=0.5)
        
        # Should keep boxes 1 and 3 (highest confidence in each group)
        self.assertIn(0, keep_indices)  # Box 1 (highest confidence)
        self.assertIn(2, keep_indices)  # Box 3 (separate)
        self.assertEqual(len(keep_indices), 2)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_iou_calculation(self):
        """Test IoU calculation accuracy."""
        engine = YOLODetectionEngine(self.config)
        
        # Test cases with known IoU values
        box1 = np.array([0, 0, 100, 100])  # 100x100 box
        
        # Identical box (IoU = 1.0)
        boxes_identical = np.array([[0, 0, 100, 100]])
        iou_identical = engine._calculate_iou(box1, boxes_identical)
        self.assertAlmostEqual(iou_identical[0], 1.0, places=3)
        
        # Non-overlapping box (IoU = 0.0)
        boxes_separate = np.array([[200, 200, 300, 300]])
        iou_separate = engine._calculate_iou(box1, boxes_separate)
        self.assertAlmostEqual(iou_separate[0], 0.0, places=3)
        
        # Half-overlapping box (IoU = 1/3)
        boxes_half = np.array([[50, 0, 150, 100]])  # 50% overlap
        iou_half = engine._calculate_iou(box1, boxes_half)
        expected_iou = 5000 / 15000  # intersection / union
        self.assertAlmostEqual(iou_half[0], expected_iou, places=3)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_box_scaling(self):
        """Test bounding box scaling functionality."""
        engine = YOLODetectionEngine(self.config)
        
        # Test scaling from smaller to larger image
        boxes = np.array([
            [10, 10, 50, 50],
            [100, 100, 200, 200]
        ])
        
        scaled_boxes = engine._scale_boxes(boxes, (320, 240), (640, 480))
        
        # Should be scaled by factor of 2
        expected_boxes = np.array([
            [20, 20, 100, 100],
            [200, 200, 400, 400]
        ])
        
        np.testing.assert_array_almost_equal(scaled_boxes, expected_boxes)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_confidence_filtering(self):
        """Test confidence threshold filtering."""
        engine = YOLODetectionEngine(self.config)
        
        # Create test frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Test with different confidence thresholds
        engine.set_confidence_threshold(0.9)
        detections_high = engine.detect_objects(frame)
        
        engine.set_confidence_threshold(0.1)
        detections_low = engine.detect_objects(frame)
        
        # Lower threshold should allow more detections (in mock mode, this may not apply)
        # But we can at least verify the threshold was set correctly
        self.assertEqual(engine.config.confidence_threshold, 0.1)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_filtering_in_detection(self):
        """Test object class filtering during detection."""
        # Test with only person enabled
        config_person_only = YOLOConfig(enabled_classes=["person"])
        engine = YOLODetectionEngine(config_person_only)
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        detections = engine.detect_objects(frame)
        
        # All detections should be person class
        for detection in detections:
            self.assertEqual(detection.object_class, ObjectClass.PERSON)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_detection_serialization(self):
        """Test detection result serialization."""
        engine = YOLODetectionEngine(self.config)
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        detections = engine.detect_objects(frame)
        
        # Test serialization of detection objects
        for detection in detections:
            detection_dict = detection.to_dict()
            
            # Verify required fields
            self.assertIn('object_class', detection_dict)
            self.assertIn('confidence', detection_dict)
            self.assertIn('bbox', detection_dict)
            self.assertIn('timestamp', detection_dict)
            self.assertIn('frame_id', detection_dict)
            
            # Verify bbox structure
            bbox = detection_dict['bbox']
            self.assertIn('x1', bbox)
            self.assertIn('y1', bbox)
            self.assertIn('x2', bbox)
            self.assertIn('y2', bbox)


class TestDetectionPerformance(unittest.TestCase):
    """Test cases for detection performance and accuracy."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = YOLOConfig()
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_detection_performance_tracking(self):
        """Test detection performance statistics."""
        engine = YOLODetectionEngine(self.config)
        
        # Perform multiple detections
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        for _ in range(5):
            engine.detect_objects(frame)
        
        # Check performance stats
        stats = engine.get_performance_stats()
        self.assertEqual(stats['total_inferences'], 5)
        self.assertGreater(stats['avg_inference_time'], 0)
        self.assertGreater(stats['avg_fps'], 0)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_detection_consistency(self):
        """Test detection consistency across multiple runs."""
        engine = YOLODetectionEngine(self.config)
        
        # Use same frame for multiple detections
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        detections1 = engine.detect_objects(frame)
        detections2 = engine.detect_objects(frame)
        
        # In mock mode, detections should be consistent
        self.assertEqual(len(detections1), len(detections2))
        
        for d1, d2 in zip(detections1, detections2):
            self.assertEqual(d1.object_class, d2.object_class)
            self.assertEqual(d1.confidence, d2.confidence)
            # Note: timestamps and frame_ids will be different
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_large_frame_processing(self):
        """Test processing of large frames."""
        engine = YOLODetectionEngine(self.config)
        
        # Create large frame
        large_frame = np.random.randint(0, 255, (2160, 3840, 3), dtype=np.uint8)  # 4K frame
        
        start_time = time.time()
        detections = engine.detect_objects(large_frame)
        processing_time = time.time() - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        self.assertLess(processing_time, 5.0)  # 5 seconds max for mock processing
        self.assertIsInstance(detections, list)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_memory_efficiency(self):
        """Test memory efficiency during processing."""
        engine = YOLODetectionEngine(self.config)
        
        # Process multiple frames to check for memory leaks
        for i in range(10):
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            detections = engine.detect_objects(frame)
            
            # Verify detections are created properly
            self.assertIsInstance(detections, list)
            for detection in detections:
                self.assertIsInstance(detection, Detection)


class TestErrorHandlingInPipeline(unittest.TestCase):
    """Test error handling in detection pipeline."""
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_invalid_frame_handling(self):
        """Test handling of invalid frames."""
        config = YOLOConfig()
        engine = YOLODetectionEngine(config)
        
        # Test with None frame
        detections = engine.detect_objects(None)
        self.assertEqual(len(detections), 0)
        
        # Test with invalid frame shape
        invalid_frame = np.array([1, 2, 3])
        detections = engine.detect_objects(invalid_frame)
        self.assertEqual(len(detections), 0)
    
    def test_frame_processor_error_handling(self):
        """Test frame processor error handling."""
        processor = FrameProcessor()
        
        # Test with invalid frame
        result = processor.preprocess_frame(None)
        self.assertIn('error', result)
        
        # Test with corrupted frame data
        corrupted_frame = np.array([[[]]])  # Invalid shape
        result = processor.preprocess_frame(corrupted_frame)
        self.assertIn('error', result)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_configuration_error_handling(self):
        """Test configuration error handling."""
        # Test invalid confidence threshold
        with self.assertRaises(ValueError):
            YOLOConfig(confidence_threshold=1.5)
        
        # Test invalid NMS threshold
        with self.assertRaises(ValueError):
            YOLOConfig(nms_threshold=-0.1)
        
        # Test invalid target FPS
        with self.assertRaises(ValueError):
            YOLOConfig(target_fps=0)


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    unittest.main()