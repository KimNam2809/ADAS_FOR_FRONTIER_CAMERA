"""
Logging configuration for ADAS Object Detection
Optimized for Edge Devices with minimal overhead
"""
import logging
import sys
from pathlib import Path
from typing import Optional
import json
from pythonjsonlogger import jsonlogger


class EdgeJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for Edge Device logging"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['timestamp'] = self.formatTime(record)
        
        # Add custom fields for Edge monitoring
        if hasattr(record, 'latency'):
            log_record['latency_ms'] = record.latency
        if hasattr(record, 'fps'):
            log_record['fps'] = record.fps
        if hasattr(record, 'memory_usage'):
            log_record['memory_usage'] = record.memory_usage
        if hasattr(record, 'gpu_usage'):
            log_record['gpu_usage'] = record.gpu_usage


def setup_logger(
    name: str = "adas",
    log_level: int = logging.INFO,
    log_file: Optional[str] = None,
    json_format: bool = False,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 3
) -> logging.Logger:
    """
    Setup logger for ADAS Object Detection
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for console only)
        json_format: Use JSON format for logs
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup log files
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatter
    if json_format:
        formatter = EdgeJSONFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        from logging.handlers import RotatingFileHandler
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "adas") -> logging.Logger:
    """Get or create a logger instance"""
    return logging.getLogger(name)


class PerformanceLogger:
    """Logger with performance metrics"""
    
    def __init__(self, name: str = "adas.performance"):
        self.logger = get_logger(name)
    
    def log_performance(
        self,
        message: str,
        latency: Optional[float] = None,
        fps: Optional[float] = None,
        memory_usage: Optional[float] = None,
        gpu_usage: Optional[float] = None,
        level: int = logging.INFO
    ):
        """Log performance metrics"""
        extra = {}
        if latency is not None:
            extra['latency'] = latency
        if fps is not None:
            extra['fps'] = fps
        if memory_usage is not None:
            extra['memory_usage'] = memory_usage
        if gpu_usage is not None:
            extra['gpu_usage'] = gpu_usage
        
        self.logger.log(level, message, extra=extra)


# Default logger instance
logger = setup_logger()
performance_logger = PerformanceLogger()
