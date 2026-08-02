"""
Performance Monitor for Edge Device Optimization
Monitors latency, FPS, CPU, GPU, and memory usage
"""
import time
import psutil
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from collections import deque
from .logger import performance_logger


@dataclass
class PerformanceMetrics:
    """Performance metrics data class"""
    latency: float = 0.0  # Processing latency in milliseconds
    fps: float = 0.0  # Frames per second
    cpu_usage: float = 0.0  # CPU usage percentage
    memory_usage: float = 0.0  # Memory usage percentage
    gpu_usage: float = 0.0  # GPU usage percentage (if available)
    gpu_memory: float = 0.0  # GPU memory usage percentage
    temperature: float = 0.0  # Device temperature in Celsius
    timestamp: float = field(default_factory=time.time)  # Timestamp


class PerformanceMonitor:
    """
    Performance monitor for Edge Device optimization
    Tracks and reports performance metrics in real-time
    """
    
    def __init__(
        self,
        window_size: int = 10,
        monitor_interval: float = 0.1,
        log_interval: float = 1.0,
        target_fps: float = 30.0,
        max_latency: float = 50.0
    ):
        """
        Initialize Performance Monitor
        
        Args:
            window_size: Number of frames to average metrics over
            monitor_interval: Time between monitoring checks (seconds)
            log_interval: Time between log entries (seconds)
            target_fps: Target frames per second
            max_latency: Maximum acceptable latency (ms)
        """
        self.window_size = window_size
        self.monitor_interval = monitor_interval
        self.log_interval = log_interval
        self.target_fps = target_fps
        self.max_latency = max_latency
        
        # Metrics history
        self.latency_history = deque(maxlen=window_size)
        self.fps_history = deque(maxlen=window_size)
        self.cpu_history = deque(maxlen=window_size)
        self.memory_history = deque(maxlen=window_size)
        self.gpu_history = deque(maxlen=window_size)
        self.gpu_memory_history = deque(maxlen=window_size)
        self.temperature_history = deque(maxlen=window_size)
        
        # Timing
        self.last_frame_time = time.time()
        self.last_log_time = time.time()
        self.frame_count = 0
        
        # GPU monitoring flag
        self.has_gpu = False
        try:
            import pynvml
            self.pynvml = pynvml
            self.pynvml.nvmlInit()
            self.has_gpu = True
        except ImportError:
            self.pynvml = None
        
        # Jetson specific
        self.is_jetson = False
        try:
            import jetson_stats
            self.jetson_stats = jetson_stats
            self.is_jetson = True
        except ImportError:
            self.jetson_stats = None
    
    def start_frame(self) -> float:
        """Mark the start of a frame processing"""
        self.frame_count += 1
        return time.time()
    
    def end_frame(self, start_time: float) -> PerformanceMetrics:
        """Mark the end of a frame processing and calculate metrics"""
        current_time = time.time()
        
        # Calculate latency
        latency = (current_time - start_time) * 1000  # Convert to ms
        self.latency_history.append(latency)
        
        # Calculate FPS
        if len(self.latency_history) > 1:
            fps = 1000.0 / (sum(self.latency_history) / len(self.latency_history))
        else:
            fps = 1000.0 / latency if latency > 0 else 0.0
        self.fps_history.append(fps)
        
        # Get system metrics
        cpu_usage = psutil.cpu_percent(interval=None)
        memory_usage = psutil.virtual_memory().percent
        self.cpu_history.append(cpu_usage)
        self.memory_history.append(memory_usage)
        
        # Get GPU metrics (if available)
        gpu_usage = 0.0
        gpu_memory = 0.0
        if self.has_gpu:
            try:
                handle = self.pynvml.nvmlDeviceGetHandleByIndex(0)
                info = self.pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_usage = info.gpu
                mem_info = self.pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_memory = (mem_info.used / mem_info.total) * 100
            except:
                pass
        self.gpu_history.append(gpu_usage)
        self.gpu_memory_history.append(gpu_memory)
        
        # Get temperature (Jetson specific)
        temperature = 0.0
        if self.is_jetson:
            try:
                temperature = self.jetson_stats.get_temp()
            except:
                pass
        self.temperature_history.append(temperature)
        
        # Log metrics if interval has passed
        if current_time - self.last_log_time >= self.log_interval:
            self._log_metrics()
            self.last_log_time = current_time
        
        # Check for performance warnings
        self._check_performance_warnings(latency, fps, cpu_usage, memory_usage)
        
        # Return current metrics
        return PerformanceMetrics(
            latency=latency,
            fps=fps,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            gpu_usage=gpu_usage,
            gpu_memory=gpu_memory,
            temperature=temperature
        )
    
    def _log_metrics(self):
        """Log aggregated performance metrics"""
        avg_latency = sum(self.latency_history) / len(self.latency_history) if self.latency_history else 0
        avg_fps = sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0
        avg_cpu = sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0
        avg_memory = sum(self.memory_history) / len(self.memory_history) if self.memory_history else 0
        avg_gpu = sum(self.gpu_history) / len(self.gpu_history) if self.gpu_history else 0
        avg_gpu_memory = sum(self.gpu_memory_history) / len(self.gpu_memory_history) if self.gpu_memory_history else 0
        avg_temp = sum(self.temperature_history) / len(self.temperature_history) if self.temperature_history else 0
        
        performance_logger.log_performance(
            "Performance Metrics",
            latency=avg_latency,
            fps=avg_fps,
            memory_usage=avg_memory,
            gpu_usage=avg_gpu
        )
    
    def _check_performance_warnings(self, latency: float, fps: float, cpu_usage: float, memory_usage: float):
        """Check for performance issues and log warnings"""
        if latency > self.max_latency:
            performance_logger.logger.warning(
                f"High latency detected: {latency:.2f}ms (target: <{self.max_latency}ms)"
            )
        
        if fps < self.target_fps * 0.8:
            performance_logger.logger.warning(
                f"Low FPS detected: {fps:.2f}fps (target: >{self.target_fps * 0.8:.2f}fps)"
            )
        
        if cpu_usage > 90:
            performance_logger.logger.warning(
                f"High CPU usage: {cpu_usage:.1f}%"
            )
        
        if memory_usage > 85:
            performance_logger.logger.warning(
                f"High memory usage: {memory_usage:.1f}%"
            )
    
    def get_average_metrics(self) -> PerformanceMetrics:
        """Get average metrics over the monitoring window"""
        return PerformanceMetrics(
            latency=sum(self.latency_history) / len(self.latency_history) if self.latency_history else 0,
            fps=sum(self.fps_history) / len(self.fps_history) if self.fps_history else 0,
            cpu_usage=sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0,
            memory_usage=sum(self.memory_history) / len(self.memory_history) if self.memory_history else 0,
            gpu_usage=sum(self.gpu_history) / len(self.gpu_history) if self.gpu_history else 0,
            gpu_memory=sum(self.gpu_memory_history) / len(self.gpu_memory_history) if self.gpu_memory_history else 0,
            temperature=sum(self.temperature_history) / len(self.temperature_history) if self.temperature_history else 0
        )
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics as dictionary"""
        metrics = self.get_average_metrics()
        return {
            "latency_ms": metrics.latency,
            "fps": metrics.fps,
            "cpu_usage_percent": metrics.cpu_usage,
            "memory_usage_percent": metrics.memory_usage,
            "gpu_usage_percent": metrics.gpu_usage,
            "gpu_memory_percent": metrics.gpu_memory,
            "temperature_celsius": metrics.temperature,
            "target_fps": self.target_fps,
            "max_latency_ms": self.max_latency,
            "meets_latency_target": metrics.latency <= self.max_latency,
            "meets_fps_target": metrics.fps >= self.target_fps
        }
    
    def reset(self):
        """Reset all metrics"""
        self.latency_history.clear()
        self.fps_history.clear()
        self.cpu_history.clear()
        self.memory_history.clear()
        self.gpu_history.clear()
        self.gpu_memory_history.clear()
        self.temperature_history.clear()
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.last_log_time = time.time()
    
    def cleanup(self):
        """Cleanup resources"""
        if self.has_gpu and self.pynvml:
            try:
                self.pynvml.nvmlShutdown()
            except:
                pass
