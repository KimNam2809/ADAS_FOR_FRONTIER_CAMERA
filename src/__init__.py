# ADAS Object Detection Module
from .config import DetectorConfig, PerformanceConfig, JetsonConfig
from .detection import YOLODetector, DetectorFactory, DetectionPostProcessor
from .utils import (
    setup_logger, 
    get_logger, 
    PerformanceMonitor, 
    FrameProcessor, 
    ModelOptimizer
)

__version__ = "1.0.0"
__all__ = [
    "DetectorConfig", 
    "PerformanceConfig", 
    "JetsonConfig",
    "YOLODetector",
    "DetectorFactory",
    "DetectionPostProcessor",
    "setup_logger",
    "get_logger",
    "PerformanceMonitor",
    "FrameProcessor",
    "ModelOptimizer"
]
