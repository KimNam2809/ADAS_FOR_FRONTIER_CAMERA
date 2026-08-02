"""
Frame Processor for Edge Device Optimization
Handles frame preprocessing, resizing, and compression
"""
import cv2
import numpy as np
from typing import Optional, Tuple, Any
from dataclasses import dataclass
from .logger import get_logger


logger = get_logger("adas.frame_processor")


@dataclass
class ProcessedFrame:
    """Processed frame data"""
    frame: np.ndarray  # Processed frame
    original_shape: Tuple[int, int]  # Original frame shape
    scale_factor: float  # Scale factor applied
    is_compressed: bool = False  # Whether frame was compressed
    compression_ratio: float = 1.0  # Compression ratio


class FrameProcessor:
    """
    Frame processor for Edge Device optimization
    Handles preprocessing, resizing, and compression of frames
    """
    
    def __init__(
        self,
        target_size: int = 640,
        enable_compression: bool = True,
        compression_quality: int = 85,
        maintain_aspect_ratio: bool = False,
        normalize: bool = True,
        bgr_to_rgb: bool = True
    ):
        """
        Initialize Frame Processor
        
        Args:
            target_size: Target size for the shorter side (or square size)
            enable_compression: Enable JPEG compression
            compression_quality: JPEG compression quality (0-100)
            maintain_aspect_ratio: Maintain aspect ratio when resizing
            normalize: Normalize pixel values to [0, 1]
            bgr_to_rgb: Convert BGR to RGB
        """
        self.target_size = target_size
        self.enable_compression = enable_compression
        self.compression_quality = compression_quality
        self.maintain_aspect_ratio = maintain_aspect_ratio
        self.normalize = normalize
        self.bgr_to_rgb = bgr_to_rgb
    
    def process(
        self,
        frame: np.ndarray,
        compress: Optional[bool] = None
    ) -> ProcessedFrame:
        """
        Process a frame for object detection
        
        Args:
            frame: Input frame (BGR format)
            compress: Override compression setting for this frame
        
        Returns:
            ProcessedFrame with processed data
        """
        start_time = cv2.getTickCount()
        
        original_shape = frame.shape[:2]  # (height, width)
        
        # Convert color space if needed
        if self.bgr_to_rgb:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Resize frame
        resized_frame, scale_factor = self._resize_frame(frame)
        
        # Normalize if needed
        if self.normalize:
            resized_frame = resized_frame.astype(np.float32) / 255.0
        
        # Compress if enabled
        is_compressed = False
        compression_ratio = 1.0
        if (self.enable_compression or compress) and self.compression_quality < 100:
            resized_frame, compression_ratio = self._compress_frame(resized_frame)
            is_compressed = True
        
        # Log processing time if significant
        processing_time = (cv2.getTickCount() - start_time) / cv2.getTickFrequency() * 1000
        if processing_time > 5:  # More than 5ms
            logger.debug(f"Frame processing took {processing_time:.2f}ms")
        
        return ProcessedFrame(
            frame=resized_frame,
            original_shape=original_shape,
            scale_factor=scale_factor,
            is_compressed=is_compressed,
            compression_ratio=compression_ratio
        )
    
    def _resize_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Resize frame to target size
        
        Returns:
            Tuple of (resized_frame, scale_factor)
        """
        h, w = frame.shape[:2]
        
        if self.maintain_aspect_ratio:
            # Maintain aspect ratio
            scale = min(self.target_size / h, self.target_size / w)
            new_h = int(h * scale)
            new_w = int(w * scale)
        else:
            # Square resize
            new_h = new_w = self.target_size
            scale = self.target_size / min(h, w)
        
        # Resize using INTER_AREA for downscaling (better quality)
        interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR
        resized = cv2.resize(frame, (new_w, new_h), interpolation=interpolation)
        
        return resized, scale
    
    def _compress_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Compress frame using JPEG compression
        
        Returns:
            Tuple of (compressed_frame, compression_ratio)
        """
        # Convert to uint8 if normalized
        if frame.dtype == np.float32:
            frame_uint8 = (frame * 255).astype(np.uint8)
        else:
            frame_uint8 = frame.astype(np.uint8)
        
        # Encode as JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.compression_quality]
        _, encoded = cv2.imencode('.jpg', frame_uint8, encode_param)
        
        # Decode back to numpy array
        compressed_frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        
        # Calculate compression ratio
        original_size = frame_uint8.nbytes
        compressed_size = len(encoded)
        compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0
        
        return compressed_frame.astype(np.float32) / 255.0, compression_ratio
    
    def batch_process(self, frames: list) -> list:
        """
        Process multiple frames in batch
        
        Args:
            frames: List of input frames
        
        Returns:
            List of ProcessedFrame objects
        """
        return [self.process(frame) for frame in frames]
    
    def get_input_tensor(
        self,
        processed_frame: ProcessedFrame,
        batch_dim: bool = True
    ) -> np.ndarray:
        """
        Convert processed frame to input tensor for model
        
        Args:
            processed_frame: ProcessedFrame object
            batch_dim: Add batch dimension
        
        Returns:
            Input tensor for model (CHW format)
        """
        frame = processed_frame.frame
        
        # Convert to CHW format
        if len(frame.shape) == 3:
            frame = np.transpose(frame, (2, 0, 1))  # HWC to CHW
        
        # Add batch dimension if needed
        if batch_dim:
            frame = np.expand_dims(frame, axis=0)
        
        return frame.astype(np.float32)
    
    def reverse_process(
        self,
        tensor: np.ndarray,
        processed_frame: ProcessedFrame
    ) -> np.ndarray:
        """
        Reverse processing to get original-like frame
        
        Args:
            tensor: Model output tensor
            processed_frame: Original ProcessedFrame
        
        Returns:
            Frame in original space
        """
        # Remove batch dimension if present
        if tensor.ndim == 4:
            tensor = tensor[0]
        
        # Convert back to HWC
        if tensor.ndim == 3:
            tensor = np.transpose(tensor, (1, 2, 0))
        
        # Denormalize if needed
        if self.normalize:
            tensor = (tensor * 255).astype(np.uint8)
        
        # Resize back to original shape
        if processed_frame.original_shape != tensor.shape[:2]:
            tensor = cv2.resize(
                tensor,
                (processed_frame.original_shape[1], processed_frame.original_shape[0]),
                interpolation=cv2.INTER_LINEAR
            )
        
        # Convert back to BGR if needed
        if self.bgr_to_rgb:
            tensor = cv2.cvtColor(tensor, cv2.COLOR_RGB2BGR)
        
        return tensor
