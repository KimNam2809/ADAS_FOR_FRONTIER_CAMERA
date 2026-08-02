"""
Performance configuration for Edge Device optimization
"""
from pydantic import BaseModel, Field
from typing import Optional


class PerformanceConfig(BaseModel):
    """Performance optimization configuration for Edge Devices"""
    
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
    
    # Bandwidth optimization
    enable_compression: bool = Field(default=True, description="Enable frame compression")
    compression_quality: int = Field(default=85, description="JPEG compression quality (0-100)")
    
    # Network optimization
    enable_batch_processing: bool = Field(default=False, description="Enable batch processing")
    batch_size: int = Field(default=1, description="Batch size for processing")
    
    # Memory optimization
    enable_memory_pool: bool = Field(default=True, description="Enable memory pooling")
    memory_pool_size: int = Field(default=10, description="Memory pool size (MB)")
    
    # Threading configuration
    num_inference_threads: int = Field(default=1, description="Number of inference threads")
    num_preprocess_threads: int = Field(default=1, description="Number of preprocessing threads")
    num_postprocess_threads: int = Field(default=1, description="Number of postprocessing threads")
    
    # Priority configuration
    priority_classes: list = Field(
        default=["person", "car", "motorcycle", "bus", "truck"],
        description="Classes with higher detection priority"
    )
    
    @classmethod
    def for_jetson_nano(cls) -> "PerformanceConfig":
        """Optimized performance config for Jetson Nano"""
        return cls(
            target_latency=50,
            max_latency=100,
            target_fps=30,
            min_fps=15,
            enable_compression=True,
            compression_quality=75,  # Lower quality for better performance
            enable_batch_processing=False,
            num_inference_threads=1,
            num_preprocess_threads=1,
            num_postprocess_threads=1
        )
    
    @classmethod
    def for_high_performance(cls) -> "PerformanceConfig":
        """High performance configuration for powerful devices"""
        return cls(
            target_latency=30,
            max_latency=60,
            target_fps=60,
            min_fps=30,
            enable_compression=True,
            compression_quality=90,
            enable_batch_processing=True,
            batch_size=4,
            num_inference_threads=2,
            num_preprocess_threads=2,
            num_postprocess_threads=2
        )
