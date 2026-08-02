"""
Configuration for Object Detection Module
Optimized for Jetson Nano and Edge Devices
"""
from pydantic import BaseModel, Field
from typing import List, Optional
import os


class DetectorConfig(BaseModel):
    """Configuration for YOLOv8 Object Detector"""
    
    # Model configuration
    model_type: str = Field(default="yolov8n", description="YOLOv8 model type (n, s, m, l, x)")
    model_path: str = Field(default="models/yolov8n.onnx", description="Path to ONNX model")
    engine_path: str = Field(default="models/yolov8n.engine", description="Path to TensorRT engine")
    
    # Detection parameters
    conf_threshold: float = Field(default=0.5, description="Confidence threshold for detections")
    iou_threshold: float = Field(default=0.45, description="IoU threshold for NMS")
    
    # Input configuration
    input_size: int = Field(default=640, description="Input image size (square)")
    
    # Classes to detect (COCO classes by default)
    target_classes: List[str] = Field(
        default=[
            "person", "bicycle", "car", "motorcycle", 
            "bus", "truck", "stop sign", "traffic light"
        ],
        description="Classes to detect (filter others)"
    )
    
    # Performance optimization
    use_tensorrt: bool = Field(default=True, description="Use TensorRT engine if available")
    use_half_precision: bool = Field(default=True, description="Use FP16 precision")
    use_int8: bool = Field(default=False, description="Use INT8 quantization")
    
    # Edge-specific optimizations
    batch_size: int = Field(default=1, description="Batch size for inference")
    num_workers: int = Field(default=1, description="Number of worker threads")
    
    # Resource limits for Jetson Nano
    max_memory_usage: float = Field(default=0.8, description="Max memory usage ratio (0-1)")
    max_gpu_usage: float = Field(default=0.9, description="Max GPU usage ratio (0-1)")
    
    @classmethod
    def for_jetson_nano(cls) -> "DetectorConfig":
        """Optimized configuration for Jetson Nano"""
        return cls(
            model_type="yolov8n",
            input_size=320,  # Smaller input for better performance
            conf_threshold=0.4,  # Lower threshold for edge devices
            use_tensorrt=True,
            use_half_precision=True,
            use_int8=True,  # Enable quantization for Jetson
            batch_size=1,
            num_workers=1
        )
    
    @classmethod
    def for_aws_g5g(cls) -> "DetectorConfig":
        """Optimized configuration for AWS G5G.xlarge"""
        return cls(
            model_type="yolov8s",
            input_size=640,
            conf_threshold=0.5,
            use_tensorrt=True,
            use_half_precision=True,
            use_int8=False,
            batch_size=4,  # Larger batch size for cloud
            num_workers=4
        )
    
    @classmethod
    def for_laptop_amd(cls) -> "DetectorConfig":
        """Optimized configuration for AMD Laptop"""
        return cls(
            model_type="yolov8s",
            input_size=640,
            conf_threshold=0.5,
            use_tensorrt=False,  # No TensorRT on AMD
            use_half_precision=False,
            use_int8=False,
            batch_size=1,
            num_workers=2
        )


class PerformanceConfig(BaseModel):
    """Performance optimization configuration"""
    
    # Latency targets (in milliseconds)
    target_latency: int = Field(default=50, description="Target processing latency (ms)")
    max_latency: int = Field(default=100, description="Maximum acceptable latency (ms)")
    
    # Throughput targets (FPS)
    target_fps: int = Field(default=30, description="Target frames per second")
    min_fps: int = Field(default=15, description="Minimum acceptable FPS")
    
    # Resource monitoring
    monitor_cpu: bool = Field(default=True, description="Monitor CPU usage")
    monitor_gpu: bool = Field(default=True, description="Monitor GPU usage")
    monitor_memory: bool = Field(default=True, description="Monitor memory usage")
    
    # Caching configuration
    enable_frame_cache: bool = Field(default=True, description="Cache frames for temporal smoothing")
    cache_size: int = Field(default=5, description="Number of frames to cache")
    
    # Power management (for Jetson)
    power_mode: str = Field(default="normal", description="Power mode: low, normal, high")


class JetsonConfig(BaseModel):
    """Jetson Nano specific configuration"""
    
    # Jetson model
    jetson_model: str = Field(default="nano", description="Jetson model: nano, tx2, xavier, orin")
    
    # JetPack version
    jetpack_version: str = Field(default="5.1.2", description="JetPack SDK version")
    
    # CUDA version
    cuda_version: str = Field(default="10.2", description="CUDA version")
    
    # TensorRT version
    tensorrt_version: str = Field(default="8.5.3", description="TensorRT version")
    
    # Memory configuration
    swap_size: str = Field(default="4G", description="Swap space size")
    
    # Cooling configuration
    fan_mode: str = Field(default="auto", description="Fan mode: auto, manual")
    max_fan_speed: int = Field(default=100, description="Maximum fan speed (%)")
    
    # Thermal throttling
    thermal_threshold: float = Field(default=80.0, description="Thermal throttling threshold (C)")
    
    @classmethod
    def get_jetson_info(cls) -> dict:
        """Get Jetson Nano hardware information"""
        try:
            import jetson_stats
            return {
                "model": jetson_stats.get_model(),
                "jetpack": jetson_stats.get_jetpack_version(),
                "cuda": jetson_stats.get_cuda_version(),
                "memory": jetson_stats.get_mem_info(),
                "cpu": jetson_stats.get_cpu_info(),
                "gpu": jetson_stats.get_gpu_info()
            }
        except ImportError:
            return {"model": "nano", "jetpack": "5.1.2", "cuda": "10.2"}
