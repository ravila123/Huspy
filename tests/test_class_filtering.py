"""
Unit tests for YOLO object class filtering functionality.

Tests class validation, enabling/disabling classes, and filtering behavior.
"""

import unittest
from unittest.mock import Mock, patch
import numpy as np

# Import the modules to test
from src.detection.yolo_engine import YOLODetectionEngine
from src.detection.config import YOLOConfig
from src.detection.models import Detection, BoundingBox, ObjectClass


class TestObjectClassFiltering(unittest.TestCase):
    """Test cases for object class filtering functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = YOLOConfig(
            confidence_threshold=0.5,
            nms_threshold=0.4,
            enabled_classes=["person", "dog", "car"]
        )
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_validation_valid_classes(self):
        """Test validation of valid class names."""
        engine = YOLODetectionEngine(self.config)
        
        # Test with valid classes
        valid_classes = ["person", "dog", "car", "bicycle"]
        invalid_classes = engine.validate_class_names(valid_classes)
        
        self.assertEqual(len(invalid_classes), 0)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_validation_invalid_classes(self):
        """Test validation of invalid class names."""
        engine = YOLODetectionEngine(self.config)
        
        # Test with mix of valid and invalid classes
        mixed_classes = ["person", "invalid_class", "dog", "nonexistent"]
        invalid_classes = engine.validate_class_names(mixed_classes)
        
        self.assertEqual(set(invalid_classes), {"invalid_class", "nonexistent"})
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_validation_empty_list(self):
        """Test validation with empty class list."""
        engine = YOLODetectionEngine(self.config)
        
        invalid_classes = engine.validate_class_names([])
        self.assertEqual(len(invalid_classes), 0)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_get_available_classes(self):
        """Test getting list of available classes."""
        engine = YOLODetectionEngine(self.config)
        
        available_classes = engine.get_available_classes()
        
        # Should return COCO classes
        self.assertIn("person", available_classes)
        self.assertIn("dog", available_classes)
        self.assertIn("car", available_classes)
        self.assertGreater(len(available_classes), 50)  # COCO has 80 classes
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_get_enabled_classes(self):
        """Test getting list of enabled classes."""
        engine = YOLODetectionEngine(self.config)
        
        enabled_classes = engine.get_enabled_classes()
        
        self.assertEqual(set(enabled_classes), {"person", "dog", "car"})
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_is_class_enabled(self):
        """Test checking if specific classes are enabled."""
        engine = YOLODetectionEngine(self.config)
        
        # Test enabled classes
        self.assertTrue(engine.is_class_enabled("person"))
        self.assertTrue(engine.is_class_enabled("dog"))
        self.assertTrue(engine.is_class_enabled("car"))
        
        # Test disabled classes
        self.assertFalse(engine.is_class_enabled("bicycle"))
        self.assertFalse(engine.is_class_enabled("cat"))
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_is_class_enabled_all_classes(self):
        """Test class checking when all classes are enabled."""
        config_all = YOLOConfig(enabled_classes=None)  # None means all enabled
        engine = YOLODetectionEngine(config_all)
        
        # All classes should be enabled
        self.assertTrue(engine.is_class_enabled("person"))
        self.assertTrue(engine.is_class_enabled("bicycle"))
        self.assertTrue(engine.is_class_enabled("cat"))
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_enable_class_valid(self):
        """Test enabling a valid class."""
        engine = YOLODetectionEngine(self.config)
        
        # Initially bicycle should not be enabled
        self.assertFalse(engine.is_class_enabled("bicycle"))
        
        # Enable bicycle
        success = engine.enable_class("bicycle")
        
        self.assertTrue(success)
        self.assertTrue(engine.is_class_enabled("bicycle"))
        self.assertIn("bicycle", engine.get_enabled_classes())
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_enable_class_invalid(self):
        """Test enabling an invalid class."""
        engine = YOLODetectionEngine(self.config)
        
        # Try to enable invalid class
        success = engine.enable_class("invalid_class")
        
        self.assertFalse(success)
        self.assertNotIn("invalid_class", engine.get_enabled_classes())
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_enable_class_already_enabled(self):
        """Test enabling a class that's already enabled."""
        engine = YOLODetectionEngine(self.config)
        
        # person is already enabled
        initial_count = len(engine.get_enabled_classes())
        success = engine.enable_class("person")
        
        self.assertTrue(success)
        self.assertEqual(len(engine.get_enabled_classes()), initial_count)  # No duplicates
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_disable_class_enabled(self):
        """Test disabling an enabled class."""
        engine = YOLODetectionEngine(self.config)
        
        # Initially person should be enabled
        self.assertTrue(engine.is_class_enabled("person"))
        
        # Disable person
        success = engine.disable_class("person")
        
        self.assertTrue(success)
        self.assertFalse(engine.is_class_enabled("person"))
        self.assertNotIn("person", engine.get_enabled_classes())
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_disable_class_not_enabled(self):
        """Test disabling a class that's not enabled."""
        engine = YOLODetectionEngine(self.config)
        
        # bicycle is not initially enabled
        success = engine.disable_class("bicycle")
        
        self.assertFalse(success)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_disable_class_all_enabled(self):
        """Test disabling a class when all classes are initially enabled."""
        config_all = YOLOConfig(enabled_classes=None)  # All enabled
        engine = YOLODetectionEngine(config_all)
        
        # Disable person
        success = engine.disable_class("person")
        
        self.assertTrue(success)
        self.assertFalse(engine.is_class_enabled("person"))
        
        # Other classes should still be enabled
        self.assertTrue(engine.is_class_enabled("dog"))
        self.assertTrue(engine.is_class_enabled("car"))
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_set_enabled_classes_valid(self):
        """Test setting enabled classes with valid class names."""
        engine = YOLODetectionEngine(self.config)
        
        new_classes = ["bicycle", "motorcycle", "bus"]
        engine.set_enabled_classes(new_classes)
        
        self.assertEqual(set(engine.get_enabled_classes()), set(new_classes))
        
        # Old classes should no longer be enabled
        self.assertFalse(engine.is_class_enabled("person"))
        self.assertFalse(engine.is_class_enabled("dog"))
        
        # New classes should be enabled
        self.assertTrue(engine.is_class_enabled("bicycle"))
        self.assertTrue(engine.is_class_enabled("motorcycle"))
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_set_enabled_classes_mixed_valid_invalid(self):
        """Test setting enabled classes with mix of valid and invalid names."""
        engine = YOLODetectionEngine(self.config)
        
        mixed_classes = ["person", "invalid_class", "dog", "nonexistent", "car"]
        engine.set_enabled_classes(mixed_classes)
        
        # Only valid classes should be enabled
        enabled_classes = engine.get_enabled_classes()
        self.assertEqual(set(enabled_classes), {"person", "dog", "car"})
        
        # Invalid classes should not be enabled
        self.assertNotIn("invalid_class", enabled_classes)
        self.assertNotIn("nonexistent", enabled_classes)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_set_enabled_classes_all_invalid(self):
        """Test setting enabled classes with all invalid names."""
        engine = YOLODetectionEngine(self.config)
        
        invalid_classes = ["invalid1", "invalid2", "nonexistent"]
        
        with self.assertRaises(ValueError):
            engine.set_enabled_classes(invalid_classes)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_filtering_in_detection(self):
        """Test that class filtering works during object detection."""
        # Test with only person enabled
        config_person_only = YOLOConfig(enabled_classes=["person"])
        engine = YOLODetectionEngine(config_person_only)
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        detections = engine.detect_objects(frame)
        
        # All detections should be person class (in mock mode)
        for detection in detections:
            self.assertEqual(detection.object_class, ObjectClass.PERSON)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_filtering_multiple_classes(self):
        """Test class filtering with multiple enabled classes."""
        config_multi = YOLOConfig(enabled_classes=["person", "dog"])
        engine = YOLODetectionEngine(config_multi)
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        detections = engine.detect_objects(frame)
        
        # All detections should be from enabled classes
        enabled_class_values = {cls.value for cls in [ObjectClass.PERSON, ObjectClass.DOG]}
        for detection in detections:
            self.assertIn(detection.object_class.value, enabled_class_values)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_filtering_no_enabled_classes(self):
        """Test detection when no classes are enabled."""
        config_none = YOLOConfig(enabled_classes=[])
        
        # This should raise an error during engine initialization
        with self.assertRaises(ValueError):
            YOLODetectionEngine(config_none)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_get_class_statistics(self):
        """Test getting class detection statistics."""
        engine = YOLODetectionEngine(self.config)
        
        stats = engine.get_class_statistics()
        
        # Should return stats for enabled classes
        self.assertIn("person", stats)
        self.assertIn("dog", stats)
        self.assertIn("car", stats)
        
        # Should not include disabled classes
        self.assertNotIn("bicycle", stats)
        
        # All counts should be integers
        for count in stats.values():
            self.assertIsInstance(count, int)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_filtering_persistence_after_reload(self):
        """Test that class filtering persists after model reload."""
        engine = YOLODetectionEngine(self.config)
        
        # Change enabled classes
        engine.set_enabled_classes(["bicycle", "motorcycle"])
        
        # Reload model
        success = engine.reload_model()
        self.assertTrue(success)
        
        # Class filtering should persist
        enabled_classes = engine.get_enabled_classes()
        self.assertEqual(set(enabled_classes), {"bicycle", "motorcycle"})
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_filtering_case_sensitivity(self):
        """Test class filtering with different case variations."""
        engine = YOLODetectionEngine(self.config)
        
        # Test case sensitivity
        invalid_classes = engine.validate_class_names(["Person", "DOG", "Car"])
        
        # Should be case sensitive - these should be invalid
        self.assertEqual(len(invalid_classes), 3)
        self.assertIn("Person", invalid_classes)
        self.assertIn("DOG", invalid_classes)
        self.assertIn("Car", invalid_classes)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_filtering_with_special_characters(self):
        """Test class filtering with special characters in names."""
        engine = YOLODetectionEngine(self.config)
        
        # Test with special characters
        special_classes = ["person!", "dog@", "car#", "traffic light"]  # traffic light is valid
        invalid_classes = engine.validate_class_names(special_classes)
        
        # Only traffic light should be valid
        self.assertEqual(len(invalid_classes), 3)
        self.assertNotIn("traffic light", invalid_classes)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_dynamic_class_filtering(self):
        """Test dynamic enabling/disabling of classes during runtime."""
        engine = YOLODetectionEngine(self.config)
        
        # Start with person, dog, car
        initial_classes = set(engine.get_enabled_classes())
        self.assertEqual(initial_classes, {"person", "dog", "car"})
        
        # Add bicycle
        engine.enable_class("bicycle")
        self.assertEqual(set(engine.get_enabled_classes()), {"person", "dog", "car", "bicycle"})
        
        # Remove dog
        engine.disable_class("dog")
        self.assertEqual(set(engine.get_enabled_classes()), {"person", "car", "bicycle"})
        
        # Add motorcycle and bus
        engine.enable_class("motorcycle")
        engine.enable_class("bus")
        self.assertEqual(set(engine.get_enabled_classes()), {"person", "car", "bicycle", "motorcycle", "bus"})


class TestClassFilteringIntegration(unittest.TestCase):
    """Integration tests for class filtering with other components."""
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_filtering_with_configuration_system(self):
        """Test class filtering integration with configuration system."""
        from src.detection.config import YOLODetectionConfig
        
        # Load configuration from file
        full_config = YOLODetectionConfig.load_from_file('config/rover_config.json')
        engine = YOLODetectionEngine(full_config.yolo)
        
        # Should respect configuration file settings
        config_classes = set(full_config.yolo.enabled_classes)
        engine_classes = set(engine.get_enabled_classes())
        self.assertEqual(config_classes, engine_classes)
    
    @patch('src.detection.yolo_engine.TORCH_AVAILABLE', False)
    def test_class_filtering_performance_impact(self):
        """Test performance impact of class filtering."""
        import time
        
        # Test with many classes enabled
        config_many = YOLOConfig(enabled_classes=["person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck"])
        engine_many = YOLODetectionEngine(config_many)
        
        # Test with few classes enabled
        config_few = YOLOConfig(enabled_classes=["person"])
        engine_few = YOLODetectionEngine(config_few)
        
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Time detection with many classes
        start_time = time.time()
        detections_many = engine_many.detect_objects(frame)
        time_many = time.time() - start_time
        
        # Time detection with few classes
        start_time = time.time()
        detections_few = engine_few.detect_objects(frame)
        time_few = time.time() - start_time
        
        # Both should complete successfully
        self.assertIsInstance(detections_many, list)
        self.assertIsInstance(detections_few, list)
        
        # Performance difference should be minimal for mock mode
        # In real implementation, fewer classes might be slightly faster
        self.assertLess(abs(time_many - time_few), 0.1)  # Within 100ms


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    unittest.main()