"""
Detector Factory for creating optimized detectors for different devices
"""
from typing import Optional
from .yolo_detector import YOLODetector
from ..config.detector_config import DetectorConfig
from ..utils.logger import get_logger


logger = get_logger("adas.detector_factory")


class DetectorFactory:
    """
    Factory class for creating optimized object detectors
    """
    
    @staticmethod
    def create_detector(
        device_type: str = "jetson_nano",
        model_path: Optional[str] = None,
        use_tensorrt: Optional[bool] = None,
        target_fps: float = 30.0
    ) -> YOLODetector:
        """
        Create an optimized detector for the specified device
        
        Args:
            device_type: Device type (jetson_nano, jetson_xavier, aws_g5g, laptop_amd)
            model_path: Path to custom model
            use_tensorrt: Force TensorRT backend
            target_fps: Target frames per second
        
        Returns:
            Configured YOLODetector instance
        """
        # Create configuration based on device type
        if device_type == "jetson_nano":
            config = DetectorConfig.for_jetson_nano()
        elif device_type == "jetson_xavier":
            config = DetectorConfig(
                model_type="yolov8s",
                input_size=640,
                use_tensorrt=True,
                use_half_precision=True,
                use_int8=False
            )
        elif device_type == "aws_g5g":
            config = DetectorConfig.for_aws_g5g()
        elif device_type == "laptop_amd":
            config = DetectorConfig.for_laptop_amd()
        else:
            logger.warning(f"Unknown device type: {device_type}, using Jetson Nano config")
            config = DetectorConfig.for_jetson_nano()
        
        # Override with custom model path if provided
        if model_path is not None:
            config.model_path = model_path
        
        # Override TensorRT setting if specified
        if use_tensorrt is not None:
            config.use_tensorrt = use_tensorrt
        
        # Create detector
        detector = YOLODetector(
            config=config,
            use_tensorrt=config.use_tensorrt,
            device="cuda" if device_type != "laptop_amd" else "cpu"
        )
        
        # Optimize for device
        detector.optimize_for_device(device_type, target_fps)
        
        logger.info(f"Created {device_type} detector with config: {config.model_type}")
        return detector
    
    @staticmethod
    def create_jetson_detector(
        model_type: str = "yolov8n",
        use_tensorrt: bool = True
    ) -> YOLODetector:
        """
        Create a detector optimized for Jetson Nano
        
        Args:
            model_type: YOLOv8 model type (n, s, m, l, x)
            use_tensorrt: Use TensorRT backend
        
        Returns:
            Jetson-optimized YOLODetector
        """
        config = DetectorConfig(
            model_type=model_type,
            input_size=320 if model_type == "n" else 640,
            use_tensorrt=use_tensorrt,
            use_half_precision=True,
            use_int8=True if model_type == "n" else False
        )
        
        detector = YOLODetector(
            config=config,
            use_tensorrt=use_tensorrt,
            device="cuda"
        )
        
        return detector
    
    @staticmethod
    def create_cloud_detector(
        model_type: str = "yolov8m",
        use_tensorrt: bool = True,
        batch_size: int = 4
    ) -> YOLODetector:
        """
        Create a detector optimized for cloud/GPU environments
        
        Args:
            model_type: YOLOv8 model type (n, s, m, l, x)
            use_tensorrt: Use TensorRT backend
            batch_size: Batch size for processing
        
        Returns:
            Cloud-optimized YOLODetector
        """
        config = DetectorConfig(
            model_type=model_type,
            input_size=640,
            use_tensorrt=use_tensorrt,
            use_half_precision=True,
            use_int8=False,
            batch_size=batch_size
        )
        
        detector = YOLODetector(
            config=config,
            use_tensorrt=use_tensorrt,
            device="cuda"
        )
        
        return detector
