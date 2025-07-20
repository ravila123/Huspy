"""
Unit tests for YOLO Detection Engine.

Tests model loading, initialization, error handling, and fallback mechanisms.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import tempfile
import os
from pathlib import Path

# Import the modules to test
from src.detection.yolo_engine import YOLODetectionEngine, ModelLoadError
from src.detection.config import YOLOConfig
from src.detection.models import Detection, BoundingBox, ObjectClass


class TestYOLODetectionEngine(unittest.TestCase):
    """Test cases for YOLODetectionEngine class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = YOLOConfig(
            enabled=True,
            model_path="models/yolov5n.pt",
            confidence_threshold=0.5,
            nms_threshold=0.4,
            enabled_classes=["person", "dog", "car"],
            device="cpu"
        )
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_init_without_torch(self):
        """Test initialization when PyTorch is not available."""
        engine = YOLODetectionEngine(self.config)
        
        # Should fall back to mock model
        self.assertEqual(engine.model_type, 'mock')
        self.assertIsNone(engine.model)
        self.assertTrue(engine.is_ready())
        self.assertGreater(len(engine.class_names), 0)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', True)
    @patch('src.detection.yolo_engine.YOLO')
    @patch('src.detection.yolo_engine.torch')
    def test_init_with_torch_success(self, mock_torch, mock_yolo_class):
        """Test successful initialization with PyTorch available."""
        # Mock torch and YOLO
        mock_torch.cuda.is_available.return_value = False
        mock_model = Mock()
        mock_model.names = {0: 'person', 1: 'bicycle', 2: 'car'}
        mock_yolo_class.return_value = mock_model
        
        # Create temporary model file
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            config = YOLOConfig(model_path=tmp_path)
            engine = YOLODetectionEngine(config)
            
            self.assertEqual(engine.model_type, 'ultralytics')
            self.assertIsNotNone(engine.model)
            self.assertTrue(engine.is_ready())
            mock_yolo_class.assert_called_once_with(tmp_path)
            mock_model.to.assert_called_once_with('cpu')
            
        finally:
            os.unlink(tmp_path)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', True)
    @patch('src.detection.yolo_engine.YOLO')
    def test_init_model_not_found_fallback(self, mock_yolo_class):
        """Test fallback when primary model file is not found."""
        # First call fails (primary model), second succeeds (fallback)
        mock_yolo_class.side_effect = [Exception("Model not found"), Mock()]
        
        engine = YOLODetectionEngine(self.config)
        
        # Should attempt multiple model loads
        self.assertGreaterEqual(mock_yolo_class.call_count, 1)
    
    def test_mock_model_detection(self):
        """Test mock model detection functionality."""
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            engine = YOLODetectionEngine(self.config)
            
            # Create test frame
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Perform detection
            detections = engine.detect_objects(frame)
            
            # Should return mock detections
            self.assertIsInstance(detections, list)
            
            # Check if enabled classes are respected
            detected_classes = [d.object_class.value for d in detections]
            for class_name in detected_classes:
                self.assertIn(class_name, self.config.enabled_classes)
    
    def test_confidence_threshold_setting(self):
        """Test setting confidence threshold."""
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            engine = YOLODetectionEngine(self.config)
            
            # Test valid threshold
            engine.set_confidence_threshold(0.7)
            self.assertEqual(engine.config.confidence_threshold, 0.7)
            
            # Test invalid threshold
            with self.assertRaises(ValueError):
                engine.set_confidence_threshold(1.5)
            
            with self.assertRaises(ValueError):
                engine.set_confidence_threshold(-0.1)
    
    def test_enabled_classes_setting(self):
        """Test setting enabled classes."""
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            engine = YOLODetectionEngine(self.config)
            
            new_classes = ["person", "bicycle"]
            engine.set_enabled_classes(new_classes)
            
            self.assertEqual(engine.config.enabled_classes, new_classes)
            
            # Check that class filtering is updated
            enabled_names = [engine.class_names[i] for i in engine.enabled_class_indices]
            for class_name in new_classes:
                if class_name in engine.class_names:
                    self.assertIn(class_name, enabled_names)
    
    def test_performance_stats(self):
        """Test performance statistics tracking."""
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            engine = YOLODetectionEngine(self.config)
            
            # Initial stats
            stats = engine.get_performance_stats()
            self.assertEqual(stats['total_inferences'], 0)
            self.assertEqual(stats['avg_inference_time'], 0.0)
            
            # Perform some detections
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            engine.detect_objects(frame)
            engine.detect_objects(frame)
            
            # Check updated stats
            stats = engine.get_performance_stats()
            self.assertEqual(stats['total_inferences'], 2)
            self.assertGreater(stats['avg_inference_time'], 0.0)
            self.assertGreater(stats['avg_fps'], 0.0)
    
    def test_model_info(self):
        """Test model information retrieval."""
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            engine = YOLODetectionEngine(self.config)
            
            info = engine.get_model_info()
            
            self.assertEqual(info['model_type'], 'mock')
            self.assertEqual(info['model_path'], self.config.model_path)
            self.assertEqual(info['device'], self.config.device)
            self.assertGreater(info['class_count'], 0)
            self.assertEqual(info['enabled_classes'], self.config.enabled_classes)
            self.assertTrue(info['is_loaded'])
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', True)
    @patch('src.detection.yolo_engine.YOLO')
    @patch('src.detection.yolo_engine.torch')
    def test_ultralytics_detection(self, mock_torch, mock_yolo_class):
        """Test detection with Ultralytics model."""
        # Mock torch and YOLO
        mock_torch.cuda.is_available.return_value = False
        
        # Mock detection results
        mock_result = Mock()
        mock_result.boxes = Mock()
        mock_result.boxes.xyxy.cpu.return_value.numpy.return_value = np.array([[100, 100, 200, 200]])
        mock_result.boxes.conf.cpu.return_value.numpy.return_value = np.array([0.85])
        mock_result.boxes.cls.cpu.return_value.numpy.return_value.astype.return_value = np.array([0])
        
        mock_model = Mock()
        mock_model.names = {0: 'person', 1: 'bicycle', 2: 'car'}
        mock_model.return_value = [mock_result]
        mock_yolo_class.return_value = mock_model
        
        # Create temporary model file
        with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            config = YOLOConfig(model_path=tmp_path, enabled_classes=['person'])
            engine = YOLODetectionEngine(config)
            
            # Perform detection
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            detections = engine.detect_objects(frame)
            
            # Verify detection results
            self.assertEqual(len(detections), 1)
            detection = detections[0]
            self.assertEqual(detection.object_class, ObjectClass.PERSON)
            self.assertEqual(detection.confidence, 0.85)
            self.assertEqual(detection.bbox.x1, 100)
            self.assertEqual(detection.bbox.y1, 100)
            self.assertEqual(detection.bbox.x2, 200)
            self.assertEqual(detection.bbox.y2, 200)
            
        finally:
            os.unlink(tmp_path)
    
    def test_class_filtering(self):
        """Test object class filtering functionality."""
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            config = YOLOConfig(enabled_classes=['person', 'dog'])
            engine = YOLODetectionEngine(config)
            
            # Perform detection
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            detections = engine.detect_objects(frame)
            
            # All detections should be from enabled classes
            for detection in detections:
                self.assertIn(detection.object_class.value, config.enabled_classes)
    
    def test_invalid_class_filtering(self):
        """Test handling of invalid class names in filtering."""
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            config = YOLOConfig(enabled_classes=['person', 'invalid_class', 'dog'])
            
            # Should not raise exception, just log warning
            engine = YOLODetectionEngine(config)
            
            # Should still work with valid classes
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            detections = engine.detect_objects(frame)
            
            # Should only detect valid classes
            detected_classes = [d.object_class.value for d in detections]
            self.assertNotIn('invalid_class', detected_classes)
    
    def test_model_reload(self):
        """Test model reloading functionality."""
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            engine = YOLODetectionEngine(self.config)
            
            original_model_type = engine.model_type
            
            # Reload model
            success = engine.reload_model()
            
            self.assertTrue(success)
            self.assertEqual(engine.model_type, original_model_type)
            self.assertTrue(engine.is_ready())
    
    @patch('src.detection.yolo_engine.ONNX_AVAILABLE', True)
    @patch('src.detection.yolo_engine.ort')
    def test_onnx_model_loading(self, mock_ort):
        """Test ONNX model loading."""
        # Mock ONNX runtime
        mock_session = Mock()
        mock_ort.InferenceSession.return_value = mock_session
        mock_ort.get_available_providers.return_value = ['CPUExecutionProvider']
        
        # Create temporary ONNX file
        with tempfile.NamedTemporaryFile(suffix='.onnx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
                config = YOLOConfig(model_path=tmp_path)
                engine = YOLODetectionEngine(config)
                
                # Should attempt ONNX loading
                mock_ort.InferenceSession.assert_called()
                
        finally:
            os.unlink(tmp_path)
    
    def test_detection_with_no_model(self):
        """Test detection behavior when model fails to load."""
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            engine = YOLODetectionEngine(self.config)
            
            # Force model to None (simulate load failure)
            engine.model = None
            engine.model_type = None
            
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            detections = engine.detect_objects(frame)
            
            # Should return empty list
            self.assertEqual(len(detections), 0)
    
    def test_detection_exception_handling(self):
        """Test exception handling during detection."""
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            engine = YOLODetectionEngine(self.config)
            
            # Mock detection method to raise exception
            with patch.object(engine, '_detect_mock', side_effect=Exception("Test error")):
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                detections = engine.detect_objects(frame)
                
                # Should handle exception gracefully
                self.assertEqual(len(detections), 0)


class TestYOLOConfigIntegration(unittest.TestCase):
    """Test integration between YOLODetectionEngine and YOLOConfig."""
    
    def test_config_validation_in_engine(self):
        """Test that engine respects config validation."""
        # Test invalid confidence threshold
        with self.assertRaises(ValueError):
            config = YOLOConfig(confidence_threshold=1.5)
        
        # Test invalid NMS threshold
        with self.assertRaises(ValueError):
            config = YOLOConfig(nms_threshold=-0.1)
        
        # Test invalid target FPS
        with self.assertRaises(ValueError):
            config = YOLOConfig(target_fps=0)
    
    def test_default_enabled_classes(self):
        """Test default enabled classes behavior."""
        config = YOLOConfig(enabled_classes=None)
        
        with patch('src.detection.yolo_engine.TORCH_AVAILABLE', False):
            engine = YOLODetectionEngine(config)
            
            # Should have default classes
            self.assertIsNotNone(engine.config.enabled_classes)
            self.assertGreater(len(engine.config.enabled_classes), 0)


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    unittest.main()