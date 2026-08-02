"""
YOLOv8 Object Detector for Edge Devices
Optimized for Jetson Nano with ONNX Runtime and TensorRT
"""
import os
import cv2
import numpy as np
import onnxruntime as ort
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

from ..config.detector_config import DetectorConfig
from ..utils.frame_processor import FrameProcessor, ProcessedFrame
from ..utils.performance_monitor import PerformanceMonitor
from ..utils.logger import get_logger
from ..utils.model_optimizer import ModelOptimizer


logger = get_logger("adas.yolo_detector")


@dataclass
class Detection:
    """Single detection result"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2) in original image coordinates
    bbox_normalized: Tuple[float, float, float, float]  # Normalized coordinates (0-1)
    
    # Additional metadata
    is_priority: bool = False
    distance: Optional[float] = None  # Estimated distance (if depth info available)
    speed: Optional[float] = None  # Estimated speed (if tracking enabled)


@dataclass
class DetectionResult:
    """Complete detection result for a frame"""
    frame_id: int
    timestamp: float
    detections: List[Detection] = field(default_factory=list)
    processing_time: float = 0.0  # Processing time in ms
    fps: float = 0.0
    
    # Performance metrics
    latency: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    gpu_usage: float = 0.0


class YOLODetector:
    """
    YOLOv8 Object Detector optimized for Edge Devices
    Supports ONNX Runtime and TensorRT backends
    """
    
    # COCO class names (80 classes)
    COCO_CLASSES = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
        "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
        "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
        "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
        "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
        "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
        "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
        "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
        "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
        "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
    ]
    
    # Priority classes for ADAS (higher priority = more important)
    PRIORITY_CLASSES = {
        "person": 1,
        "car": 2,
        "motorcycle": 2,
        "bus": 2,
        "truck": 2,
        "bicycle": 3,
        "stop sign": 1,
        "traffic light": 1
    }
    
    def __init__(
        self,
        config: Optional[DetectorConfig] = None,
        model_path: Optional[str] = None,
        use_tensorrt: Optional[bool] = None,
        device: str = "cuda"  # or "cpu"
    ):
        """
        Initialize YOLOv8 Detector
        
        Args:
            config: Detector configuration
            model_path: Path to ONNX or TensorRT model
            use_tensorrt: Force TensorRT backend
            device: Device to use (cuda or cpu)
        """
        # Load configuration
        if config is None:
            config = DetectorConfig.for_jetson_nano()
        self.config = config
        
        # Override with parameters
        if model_path is not None:
            self.config.model_path = model_path
        if use_tensorrt is not None:
            self.config.use_tensorrt = use_tensorrt
        
        self.device = device
        self.session = None
        self.input_name = None
        self.output_names = None
        self.frame_processor = None
        self.performance_monitor = None
        self.frame_id = 0
        
        # Initialize components
        self._initialize_session()
        self._initialize_frame_processor()
        self._initialize_performance_monitor()
        
        logger.info(f"YOLOv8 Detector initialized with config: {self.config.model_type}")
    
    def _initialize_session(self):
        """Initialize ONNX Runtime or TensorRT session"""
        try:
            # Try TensorRT first if enabled
            if self.config.use_tensorrt and self._try_tensorrt():
                return
            
            # Fall back to ONNX Runtime
            self._initialize_onnx_runtime()
            
        except Exception as e:
            logger.error(f"Failed to initialize inference session: {e}")
            raise
    
    def _try_tensorrt(self) -> bool:
        """Try to initialize TensorRT engine"""
        try:
            import tensorrt as trt
            
            if not os.path.exists(self.config.engine_path):
                logger.warning(f"TensorRT engine not found: {self.config.engine_path}")
                return False
            
            # Load TensorRT engine
            TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
            with open(self.config.engine_path, "rb") as model:
                runtime = trt.Runtime(TRT_LOGGER)
                engine = runtime.deserialize_cuda_engine(model.read())
            
            # Create execution context
            context = engine.create_execution_context()
            
            # Store TensorRT components
            self.trt_engine = engine
            self.trt_context = context
            self.trt_runtime = runtime
            
            # Get input/output names
            self.input_name = engine.get_binding_name(0)
            self.output_names = [engine.get_binding_name(i) for i in range(1, engine.num_bindings)]
            
            logger.info("Initialized TensorRT engine successfully")
            return True
            
        except ImportError:
            logger.warning("TensorRT not available")
            return False
        except Exception as e:
            logger.warning(f"Failed to load TensorRT engine: {e}")
            return False
    
    def _initialize_onnx_runtime(self):
        """Initialize ONNX Runtime session"""
        # Set providers based on device
        providers = []
        if self.device == "cuda":
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        else:
            providers = ['CPUExecutionProvider']
        
        # Create session options
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Enable FP16 if configured
        if self.config.use_half_precision:
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        # Load model
        if not os.path.exists(self.config.model_path):
            raise FileNotFoundError(f"Model not found: {self.config.model_path}")
        
        self.session = ort.InferenceSession(
            self.config.model_path,
            providers=providers,
            sess_options=options
        )
        
        # Get input/output names
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [output.name for output in self.session.get_outputs()]
        
        logger.info(f"Initialized ONNX Runtime with providers: {providers}")
    
    def _initialize_frame_processor(self):
        """Initialize frame processor"""
        self.frame_processor = FrameProcessor(
            target_size=self.config.input_size,
            enable_compression=self.config.enable_frame_cache if hasattr(self.config, 'enable_frame_cache') else False,
            compression_quality=90,
            maintain_aspect_ratio=False,
            normalize=True,
            bgr_to_rgb=True
        )
    
    def _initialize_performance_monitor(self):
        """Initialize performance monitor"""
        self.performance_monitor = PerformanceMonitor(
            window_size=10,
            target_fps=self.config.target_fps if hasattr(self.config, 'target_fps') else 30,
            max_latency=self.config.max_latency if hasattr(self.config, 'max_latency') else 50
        )
    
    def detect(
        self,
        frame: np.ndarray,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None
    ) -> DetectionResult:
        """
        Perform object detection on a frame
        
        Args:
            frame: Input frame (BGR format)
            conf_threshold: Override confidence threshold
            iou_threshold: Override IoU threshold
        
        Returns:
            DetectionResult with detections and metrics
        """
        # Use config values if not provided
        conf_threshold = conf_threshold or self.config.conf_threshold
        iou_threshold = iou_threshold or self.config.iou_threshold
        
        # Start timing
        start_time = self.performance_monitor.start_frame()
        
        # Process frame
        processed_frame = self.frame_processor.process(frame)
        
        # Prepare input tensor
        input_tensor = self.frame_processor.get_input_tensor(processed_frame)
        
        # Run inference
        detections = self._run_inference(input_tensor)
        
        # Post-process detections
        detections = self._post_process(
            detections,
            processed_frame,
            conf_threshold,
            iou_threshold
        )
        
        # Filter by target classes
        detections = [d for d in detections if d.class_name in self.config.target_classes]
        
        # Mark priority detections
        for detection in detections:
            detection.is_priority = detection.class_name in self.PRIORITY_CLASSES
        
        # End timing and get metrics
        metrics = self.performance_monitor.end_frame(start_time)
        
        # Create result
        self.frame_id += 1
        result = DetectionResult(
            frame_id=self.frame_id,
            timestamp=start_time,
            detections=detections,
            processing_time=metrics.latency,
            fps=metrics.fps,
            latency=metrics.latency,
            cpu_usage=metrics.cpu_usage,
            memory_usage=metrics.memory_usage,
            gpu_usage=metrics.gpu_usage
        )
        
        return result
    
    def _run_inference(self, input_tensor: np.ndarray) -> List[np.ndarray]:
        """
        Run inference using the current backend
        
        Args:
            input_tensor: Input tensor for the model
        
        Returns:
            List of output tensors
        """
        try:
            # TensorRT inference
            if hasattr(self, 'trt_context'):
                return self._run_tensorrt_inference(input_tensor)
            
            # ONNX Runtime inference
            return self._run_onnx_inference(input_tensor)
            
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise
    
    def _run_onnx_inference(self, input_tensor: np.ndarray) -> List[np.ndarray]:
        """Run ONNX Runtime inference"""
        inputs = {self.input_name: input_tensor}
        outputs = self.session.run(self.output_names, inputs)
        return outputs
    
    def _run_tensorrt_inference(self, input_tensor: np.ndarray) -> List[np.ndarray]:
        """Run TensorRT inference"""
        import pycuda.driver as cuda
        import pycuda.autoinit
        
        # Allocate device memory
        input_shape = input_tensor.shape
        input_size = np.prod(input_shape) * input_tensor.dtype.itemsize
        
        # Create CUDA buffers
        d_input = cuda.mem_alloc(input_size)
        d_outputs = []
        
        # Copy input to device
        cuda.memcpy_htod(d_input, input_tensor.ravel())
        
        # Get output sizes
        for binding in range(1, self.trt_engine.num_bindings):
            binding_name = self.trt_engine.get_binding_name(binding)
            binding_shape = self.trt_engine.get_binding_shape(binding)
            output_size = np.prod(binding_shape) * 4  # Assuming FP32
            d_outputs.append(cuda.mem_alloc(output_size))
        
        # Execute inference
        bindings = [int(d_input)] + [int(d_output) for d_output in d_outputs]
        self.trt_context.execute_async_v2(bindings=bindings)
        
        # Synchronize
        cuda.Context.synchronize()
        
        # Copy outputs back to host
        outputs = []
        for d_output in d_outputs:
            output_shape = self.trt_engine.get_binding_shape(len(d_outputs) + 1)
            output = np.empty(output_shape, dtype=np.float32)
            cuda.memcpy_dtoh(output.ravel(), d_output)
            outputs.append(output)
        
        # Free device memory
        for d_output in d_outputs:
            d_output.free()
        d_input.free()
        
        return outputs
    
    def _post_process(
        self,
        outputs: List[np.ndarray],
        processed_frame: ProcessedFrame,
        conf_threshold: float,
        iou_threshold: float
    ) -> List[Detection]:
        """
        Post-process model outputs to get detections
        
        Args:
            outputs: Model outputs
            processed_frame: Processed frame information
            conf_threshold: Confidence threshold
            iou_threshold: IoU threshold for NMS
        
        Returns:
            List of Detection objects
        """
        # YOLOv8 output format: [batch, num_detections, 6] where 6 = [x, y, w, h, conf, class]
        # For ONNX model, output is typically a list of tensors
        if len(outputs) == 1:
            # Single output tensor (common for YOLOv8 ONNX)
            predictions = outputs[0]
        else:
            # Multiple outputs (might need to combine)
            predictions = outputs[0]
        
        # Reshape predictions
        predictions = np.squeeze(predictions)  # Remove batch dimension
        
        # Filter by confidence threshold
        conf_mask = predictions[:, 4] >= conf_threshold
        predictions = predictions[conf_mask]
        
        # Convert from cx, cy, w, h to x1, y1, x2, y2
        boxes = self._convert_box_format(predictions[:, :4])
        
        # Scale boxes back to original image size
        original_h, original_w = processed_frame.original_shape
        scale_factor = processed_frame.scale_factor
        boxes = self._scale_boxes(boxes, scale_factor, original_w, original_h)
        
        # Apply NMS
        keep_indices = self._non_max_suppression(
            boxes,
            predictions[:, 4],  # Confidences
            iou_threshold
        )
        
        # Create Detection objects
        detections = []
        for idx in keep_indices:
            x1, y1, x2, y2 = boxes[idx]
            conf = float(predictions[idx, 4])
            class_id = int(predictions[idx, 5])
            class_name = self.COCO_CLASSES[class_id] if class_id < len(self.COCO_CLASSES) else f"class_{class_id}"
            
            # Calculate normalized coordinates
            bbox_normalized = (
                x1 / original_w,
                y1 / original_h,
                x2 / original_w,
                y2 / original_h
            )
            
            detection = Detection(
                class_id=class_id,
                class_name=class_name,
                confidence=conf,
                bbox=(x1, y1, x2, y2),
                bbox_normalized=bbox_normalized
            )
            detections.append(detection)
        
        return detections
    
    def _convert_box_format(self, boxes: np.ndarray) -> np.ndarray:
        """
        Convert boxes from center x, center y, width, height to x1, y1, x2, y2
        
        Args:
            boxes: Array of boxes in [cx, cy, w, h] format
        
        Returns:
            Array of boxes in [x1, y1, x2, y2] format
        """
        x1 = boxes[:, 0] - boxes[:, 2] / 2
        y1 = boxes[:, 1] - boxes[:, 3] / 2
        x2 = boxes[:, 0] + boxes[:, 2] / 2
        y2 = boxes[:, 1] + boxes[:, 3] / 2
        return np.column_stack([x1, y1, x2, y2])
    
    def _scale_boxes(
        self,
        boxes: np.ndarray,
        scale_factor: float,
        target_width: int,
        target_height: int
    ) -> np.ndarray:
        """
        Scale boxes to target dimensions
        
        Args:
            boxes: Array of boxes in [x1, y1, x2, y2] format
            scale_factor: Scale factor from preprocessing
            target_width: Target width
            target_height: Target height
        
        Returns:
            Scaled boxes
        """
        # Scale coordinates
        boxes[:, [0, 2]] *= target_width  # x1, x2
        boxes[:, [1, 3]] *= target_height  # y1, y2
        
        # Clip to image boundaries
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, target_width)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, target_height)
        
        return boxes
    
    def _non_max_suppression(
        self,
        boxes: np.ndarray,
        scores: np.ndarray,
        iou_threshold: float
    ) -> np.ndarray:
        """
        Apply Non-Maximum Suppression to remove overlapping boxes
        
        Args:
            boxes: Array of boxes in [x1, y1, x2, y2] format
            scores: Array of confidence scores
            iou_threshold: IoU threshold for suppression
        
        Returns:
            Indices of kept boxes
        """
        if len(boxes) == 0:
            return np.array([], dtype=int)
        
        # Sort by score (descending)
        sorted_indices = np.argsort(scores)[::-1]
        boxes = boxes[sorted_indices]
        scores = scores[sorted_indices]
        
        # Calculate IoU matrix
        iou_matrix = self._calculate_iou(boxes, boxes)
        
        # Apply NMS
        keep = []
        while len(sorted_indices) > 0:
            # Pick the box with highest score
            last = len(sorted_indices) - 1
            i = sorted_indices[last]
            keep.append(i)
            
            # Find indices of boxes with IoU > threshold
            ious = iou_matrix[last, :-1]
            to_remove = np.where(ious > iou_threshold)[0]
            
            # Remove these boxes
            sorted_indices = np.delete(sorted_indices, to_remove)
            iou_matrix = np.delete(iou_matrix, to_remove, axis=0)
            iou_matrix = np.delete(iou_matrix, to_remove, axis=1)
        
        return np.array(keep, dtype=int)
    
    def _calculate_iou(self, boxes1: np.ndarray, boxes2: np.ndarray) -> np.ndarray:
        """
        Calculate Intersection over Union (IoU) between two sets of boxes
        
        Args:
            boxes1: Array of boxes in [x1, y1, x2, y2] format
            boxes2: Array of boxes in [x1, y1, x2, y2] format
        
        Returns:
            IoU matrix (len(boxes1) x len(boxes2))
        """
        # Calculate intersection areas
        x1 = np.maximum(boxes1[:, 0][:, None], boxes2[:, 0][None, :])
        y1 = np.maximum(boxes1[:, 1][:, None], boxes2[:, 1][None, :])
        x2 = np.minimum(boxes1[:, 2][:, None], boxes2[:, 2][None, :])
        y2 = np.minimum(boxes1[:, 3][:, None], boxes2[:, 3][None, :])
        
        intersection = np.maximum(x2 - x1, 0) * np.maximum(y2 - y1, 0)
        
        # Calculate areas of each box
        area1 = (boxes1[:, 2] - boxes1[:, 0]) * (boxes1[:, 3] - boxes1[:, 1])
        area2 = (boxes2[:, 2] - boxes2[:, 0]) * (boxes2[:, 3] - boxes2[:, 1])
        
        # Calculate union areas
        union = area1[:, None] + area2[None, :] - intersection
        
        # Calculate IoU
        iou = intersection / union
        
        return iou
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return self.performance_monitor.get_current_metrics()
    
    def reset_performance_metrics(self):
        """Reset performance metrics"""
        self.performance_monitor.reset()
    
    def optimize_for_device(
        self,
        device_type: str = "jetson_nano",
        target_fps: float = 30.0
    ):
        """
        Optimize detector for specific device
        
        Args:
            device_type: Device type (jetson_nano, jetson_xavier, aws_g5g, laptop_amd)
            target_fps: Target frames per second
        """
        # Get optimization recommendations
        optimizer = ModelOptimizer()
        recommendations = optimizer.get_optimization_recommendations(device_type, target_fps)
        
        # Update configuration based on recommendations
        if device_type == "jetson_nano":
            self.config.model_type = "yolov8n"
            self.config.input_size = 320
            self.config.use_tensorrt = True
            self.config.use_half_precision = True
            self.config.use_int8 = True
        elif device_type == "jetson_xavier":
            self.config.model_type = "yolov8s"
            self.config.input_size = 640
            self.config.use_tensorrt = True
            self.config.use_half_precision = True
        elif device_type == "aws_g5g":
            self.config.model_type = "yolov8m"
            self.config.input_size = 640
            self.config.use_tensorrt = True
            self.config.use_half_precision = True
        elif device_type == "laptop_amd":
            self.config.model_type = "yolov8s"
            self.config.input_size = 640
            self.config.use_tensorrt = False
            self.config.use_half_precision = False
        
        # Reinitialize with new config
        self._initialize_frame_processor()
        
        logger.info(f"Optimized detector for {device_type} with target FPS: {target_fps}")
    
    def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, 'session'):
            del self.session
        if hasattr(self, 'trt_context'):
            del self.trt_context
        if hasattr(self, 'trt_engine'):
            del self.trt_engine
        if hasattr(self, 'trt_runtime'):
            del self.trt_runtime
        if hasattr(self, 'performance_monitor'):
            self.performance_monitor.cleanup()
