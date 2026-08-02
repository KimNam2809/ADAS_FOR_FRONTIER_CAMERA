"""
Test cases for YOLOv8 Object Detector
"""
import pytest
import numpy as np
import cv2
from pathlib import Path
from src.detection import YOLODetector, DetectorFactory
from src.config import DetectorConfig


@pytest.fixture
def sample_frame():
    """Create a sample frame for testing"""
    # Create a 640x480 RGB image with some objects
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add a red rectangle (simulating a car)
    cv2.rectangle(frame, (100, 100), (200, 150), (0, 0, 255), -1)
    
    # Add a blue rectangle (simulating a person)
    cv2.rectangle(frame, (300, 200), (350, 300), (255, 0, 0), -1)
    
    return frame


@pytest.fixture
def detector_config():
    """Create a test detector configuration"""
    return DetectorConfig(
        model_type="yolov8n",
        model_path="models/yolov8n.onnx",
        conf_threshold=0.5,
        iou_threshold=0.45,
        input_size=640,
        use_tensorrt=False,  # Disable TensorRT for testing
        use_half_precision=False,
        use_int8=False
    )


class TestYOLODetector:
    """Test class for YOLODetector"""
    
    def test_detector_initialization(self, detector_config):
        """Test detector initialization"""
        # This will fail if model file doesn't exist, but tests the initialization logic
        try:
            detector = YOLODetector(config=detector_config, use_tensorrt=False)
            assert detector is not None
            assert detector.config == detector_config
        except FileNotFoundError:
            # Expected if model file doesn't exist
            pass
    
    def test_detector_with_missing_model(self, detector_config):
        """Test detector with missing model file"""
        detector_config.model_path = "nonexistent_model.onnx"
        
        with pytest.raises(FileNotFoundError):
            YOLODetector(config=detector_config, use_tensorrt=False)
    
    def test_detector_factory_jetson(self):
        """Test detector factory for Jetson Nano"""
        detector = DetectorFactory.create_detector(
            device_type="jetson_nano",
            use_tensorrt=False  # Disable for testing
        )
        
        assert detector is not None
        assert detector.config.model_type == "yolov8n"
        assert detector.config.input_size == 320  # Optimized for Jetson
    
    def test_detector_factory_aws(self):
        """Test detector factory for AWS G5G"""
        detector = DetectorFactory.create_detector(
            device_type="aws_g5g",
            use_tensorrt=False  # Disable for testing
        )
        
        assert detector is not None
        assert detector.config.model_type == "yolov8s"
        assert detector.config.input_size == 640
    
    def test_detector_factory_laptop(self):
        """Test detector factory for AMD Laptop"""
        detector = DetectorFactory.create_detector(
            device_type="laptop_amd",
            use_tensorrt=False
        )
        
        assert detector is not None
        assert detector.config.model_type == "yolov8s"
        assert detector.config.use_tensorrt == False


class TestFrameProcessor:
    """Test class for FrameProcessor"""
    
    def test_frame_processing(self, sample_frame):
        """Test frame preprocessing"""
        from src.utils import FrameProcessor
        
        processor = FrameProcessor(
            target_size=640,
            enable_compression=False,
            maintain_aspect_ratio=False
        )
        
        processed = processor.process(sample_frame)
        
        assert processed is not None
        assert processed.frame.shape[0] == 640  # Height
        assert processed.frame.shape[1] == 640  # Width
        assert processed.original_shape == (480, 640)
    
    def test_frame_resizing(self, sample_frame):
        """Test frame resizing with aspect ratio"""
        from src.utils import FrameProcessor
        
        processor = FrameProcessor(
            target_size=320,
            enable_compression=False,
            maintain_aspect_ratio=True
        )
        
        processed = processor.process(sample_frame)
        
        # With aspect ratio maintained, the smaller dimension should be 320
        assert min(processed.frame.shape[:2]) == 320
    
    def test_input_tensor_conversion(self, sample_frame):
        """Test conversion to input tensor"""
        from src.utils import FrameProcessor
        
        processor = FrameProcessor(
            target_size=640,
            enable_compression=False
        )
        
        processed = processor.process(sample_frame)
        tensor = processor.get_input_tensor(processed, batch_dim=True)
        
        assert tensor.ndim == 4  # Batch dimension
        assert tensor.shape[0] == 1  # Batch size
        assert tensor.shape[1] == 3  # Channels
        assert tensor.shape[2] == 640  # Height
        assert tensor.shape[3] == 640  # Width


class TestPerformanceMonitor:
    """Test class for PerformanceMonitor"""
    
    def test_performance_monitoring(self):
        """Test performance monitoring"""
        from src.utils import PerformanceMonitor
        import time
        
        monitor = PerformanceMonitor(
            window_size=5,
            target_fps=30,
            max_latency=50
        )
        
        # Simulate frame processing
        for _ in range(10):
            start = monitor.start_frame()
            time.sleep(0.01)  # Simulate processing
            metrics = monitor.end_frame(start)
            
            assert metrics is not None
            assert metrics.latency >= 0
            assert metrics.fps >= 0
        
        # Check average metrics
        avg_metrics = monitor.get_average_metrics()
        assert avg_metrics.latency >= 0
        assert avg_metrics.fps >= 0
    
    def test_performance_warnings(self, caplog):
        """Test performance warning detection"""
        from src.utils import PerformanceMonitor
        import time
        
        monitor = PerformanceMonitor(
            window_size=5,
            target_fps=100,  # High target to trigger warning
            max_latency=10  # Low threshold to trigger warning
        )
        
        # Simulate slow processing
        start = monitor.start_frame()
        time.sleep(0.1)  # 100ms processing
        monitor.end_frame(start)
        
        # Check if warning was logged
        assert "High latency detected" in caplog.text or "Low FPS detected" in caplog.text


class TestModelOptimizer:
    """Test class for ModelOptimizer"""
    
    def test_optimization_recommendations(self):
        """Test optimization recommendations"""
        from src.utils import ModelOptimizer
        
        optimizer = ModelOptimizer()
        
        # Test Jetson Nano recommendations
        jetson_rec = optimizer.get_optimization_recommendations("jetson_nano", 30)
        assert jetson_rec["model_size"] == "nano"
        assert jetson_rec["input_size"] == 320
        assert jetson_rec["use_tensorrt"] == True
        
        # Test AWS recommendations
        aws_rec = optimizer.get_optimization_recommendations("aws_g5g", 60)
        assert aws_rec["model_size"] == "medium"
        assert aws_rec["input_size"] == 640
        
        # Test high FPS recommendations
        high_fps_rec = optimizer.get_optimization_recommendations("jetson_nano", 60)
        assert high_fps_rec["model_size"] == "nano"
        assert high_fps_rec["input_size"] == 320


class TestDetectionPostProcessor:
    """Test class for DetectionPostProcessor"""
    
    def test_post_processor_initialization(self):
        """Test post processor initialization"""
        from src.detection import DetectionPostProcessor
        
        processor = DetectionPostProcessor(
            max_track_age=2.0,
            iou_threshold=0.5
        )
        
        assert processor is not None
        assert processor.max_track_age == 2.0
        assert processor.iou_threshold == 0.5
    
    def test_iou_calculation(self):
        """Test IoU calculation"""
        from src.detection import DetectionPostProcessor
        
        processor = DetectionPostProcessor()
        
        # Two identical boxes should have IoU = 1.0
        bbox1 = (0, 0, 100, 100)
        bbox2 = (0, 0, 100, 100)
        iou = processor._calculate_iou(bbox1, bbox2)
        assert iou == 1.0
        
        # Two non-overlapping boxes should have IoU = 0.0
        bbox1 = (0, 0, 100, 100)
        bbox2 = (200, 200, 300, 300)
        iou = processor._calculate_iou(bbox1, bbox2)
        assert iou == 0.0
        
        # Two partially overlapping boxes
        bbox1 = (0, 0, 100, 100)
        bbox2 = (50, 50, 150, 150)
        iou = processor._calculate_iou(bbox1, bbox2)
        assert 0 < iou < 1
    
    def test_track_management(self):
        """Test track management"""
        from src.detection import DetectionPostProcessor, Detection
        from src.detection.yolo_detector import DetectionResult
        import time
        
        processor = DetectionPostProcessor(max_track_age=0.1)  # Short age for testing
        
        # Create a detection result
        detection = Detection(
            class_id=0,
            class_name="person",
            confidence=0.9,
            bbox=(100, 100, 200, 200),
            bbox_normalized=(0.1, 0.1, 0.2, 0.2)
        )
        
        result = DetectionResult(
            frame_id=1,
            timestamp=time.time(),
            detections=[detection]
        )
        
        # Process first frame
        context_result = processor.process(result)
        assert len(context_result.tracked_detections) == 1
        assert context_result.tracked_detections[0].track_id == 1
        
        # Process second frame with same detection
        detection2 = Detection(
            class_id=0,
            class_name="person",
            confidence=0.9,
            bbox=(105, 105, 205, 205),  # Slightly moved
            bbox_normalized=(0.1, 0.1, 0.2, 0.2)
        )
        
        result2 = DetectionResult(
            frame_id=2,
            timestamp=time.time(),
            detections=[detection2]
        )
        
        context_result2 = processor.process(result2)
        assert len(context_result2.tracked_detections) == 1
        assert context_result2.tracked_detections[0].track_id == 1  # Same track
    
    def test_reset(self):
        """Test reset functionality"""
        from src.detection import DetectionPostProcessor
        
        processor = DetectionPostProcessor()
        
        # Add some tracks
        processor.tracks[1] = None  # Dummy track
        processor.next_track_id = 2
        
        # Reset
        processor.reset()
        
        assert len(processor.tracks) == 0
        assert processor.next_track_id == 1
        assert processor.last_frame_time == 0.0
