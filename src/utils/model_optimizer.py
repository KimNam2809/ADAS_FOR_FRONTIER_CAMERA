"""
Model Optimizer for Edge Device Deployment
Handles model quantization, pruning, and TensorRT optimization
"""
import os
import onnx
import onnxruntime as ort
from typing import Optional, Tuple, Any
from pathlib import Path
from .logger import get_logger


logger = get_logger("adas.model_optimizer")


class ModelOptimizer:
    """
    Model optimizer for Edge Device deployment
    Handles ONNX export, quantization, and TensorRT optimization
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        output_dir: str = "models",
        use_tensorrt: bool = True,
        use_half_precision: bool = True,
        use_int8: bool = False
    ):
        """
        Initialize Model Optimizer
        
        Args:
            model_path: Path to the original model (PyTorch, ONNX, etc.)
            output_dir: Directory to save optimized models
            use_tensorrt: Enable TensorRT optimization
            use_half_precision: Use FP16 precision
            use_int8: Use INT8 quantization
        """
        self.model_path = model_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_tensorrt = use_tensorrt
        self.use_half_precision = use_half_precision
        self.use_int8 = use_int8
        
        # Check for TensorRT availability
        self.has_tensorrt = False
        try:
            import tensorrt as trt
            self.trt = trt
            self.has_tensorrt = True
            logger.info("TensorRT is available")
        except ImportError:
            logger.warning("TensorRT is not available")
    
    def export_to_onnx(
        self,
        model,
        input_shape: Tuple[int, ...] = (1, 3, 640, 640),
        onnx_path: Optional[str] = None
    ) -> str:
        """
        Export PyTorch model to ONNX format
        
        Args:
            model: PyTorch model
            input_shape: Input tensor shape (batch, channels, height, width)
            onnx_path: Output ONNX file path (optional)
        
        Returns:
            Path to exported ONNX model
        """
        if onnx_path is None:
            model_name = os.path.splitext(os.path.basename(self.model_path or "model"))[0]
            onnx_path = str(self.output_dir / f"{model_name}.onnx")
        
        # Create dummy input
        import torch
        dummy_input = torch.randn(*input_shape)
        
        # Export to ONNX
        logger.info(f"Exporting model to ONNX: {onnx_path}")
        torch.onnx.export(
            model,
            dummy_input,
            onnx_path,
            export_params=True,
            opset_version=13,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={
                'input': {0: 'batch_size'},
                'output': {0: 'batch_size'}
            }
        )
        
        # Validate ONNX model
        self._validate_onnx(onnx_path)
        
        logger.info(f"ONNX model exported successfully: {onnx_path}")
        return onnx_path
    
    def _validate_onnx(self, onnx_path: str) -> bool:
        """Validate ONNX model"""
        try:
            model = onnx.load(onnx_path)
            onnx.checker.check_model(model)
            logger.info(f"ONNX model validation passed: {onnx_path}")
            return True
        except onnx.checker.ValidationError as e:
            logger.error(f"ONNX model validation failed: {e}")
            return False
    
    def quantize_onnx(
        self,
        onnx_path: str,
        quantization_type: str = "fp16",
        calibration_data: Optional[list] = None,
        quantized_path: Optional[str] = None
    ) -> str:
        """
        Quantize ONNX model
        
        Args:
            onnx_path: Path to ONNX model
            quantization_type: "fp16" or "int8"
            calibration_data: Calibration data for INT8 quantization
            quantized_path: Output path for quantized model
        
        Returns:
            Path to quantized ONNX model
        """
        if quantization_type == "fp16":
            return self._quantize_fp16(onnx_path, quantized_path)
        elif quantization_type == "int8":
            return self._quantize_int8(onnx_path, calibration_data, quantized_path)
        else:
            raise ValueError(f"Unsupported quantization type: {quantization_type}")
    
    def _quantize_fp16(self, onnx_path: str, output_path: Optional[str] = None) -> str:
        """Quantize ONNX model to FP16"""
        if output_path is None:
            model_name = os.path.splitext(os.path.basename(onnx_path))[0]
            output_path = str(self.output_dir / f"{model_name}_fp16.onnx")
        
        logger.info(f"Quantizing model to FP16: {output_path}")
        
        # Load ONNX model
        model = onnx.load(onnx_path)
        
        # Convert to FP16
        from onnxconverter_common import float16
        model_fp16 = float16.convert_float_to_float16(model)
        
        # Save quantized model
        onnx.save(model_fp16, output_path)
        
        logger.info(f"FP16 quantization completed: {output_path}")
        return output_path
    
    def _quantize_int8(
        self,
        onnx_path: str,
        calibration_data: Optional[list] = None,
        output_path: Optional[str] = None
    ) -> str:
        """Quantize ONNX model to INT8"""
        if output_path is None:
            model_name = os.path.splitext(os.path.basename(onnx_path))[0]
            output_path = str(self.output_dir / f"{model_name}_int8.onnx")
        
        if calibration_data is None:
            raise ValueError("Calibration data is required for INT8 quantization")
        
        logger.info(f"Quantizing model to INT8: {output_path}")
        
        # Use onnxruntime quantization
        from onnxruntime.quantization import quantize_dynamic, QuantType
        
        # Quantize with dynamic range
        quantize_dynamic(
            onnx_path,
            output_path,
            weight_type=QuantType.QUInt8
        )
        
        logger.info(f"INT8 quantization completed: {output_path}")
        return output_path
    
    def optimize_for_tensorrt(
        self,
        onnx_path: str,
        engine_path: Optional[str] = None,
        fp16_mode: bool = True,
        int8_mode: bool = False,
        max_batch_size: int = 1,
        workspace_size: int = 1 << 20  # 1MB
    ) -> str:
        """
        Optimize ONNX model for TensorRT
        
        Args:
            onnx_path: Path to ONNX model
            engine_path: Output path for TensorRT engine
            fp16_mode: Enable FP16 precision
            int8_mode: Enable INT8 precision
            max_batch_size: Maximum batch size
            workspace_size: Maximum workspace size in bytes
        
        Returns:
            Path to TensorRT engine
        """
        if not self.has_tensorrt:
            raise RuntimeError("TensorRT is not available")
        
        if engine_path is None:
            model_name = os.path.splitext(os.path.basename(onnx_path))[0]
            engine_path = str(self.output_dir / f"{model_name}.engine")
        
        logger.info(f"Building TensorRT engine: {engine_path}")
        
        # Create TensorRT logger
        TRT_LOGGER = self.trt.Logger(self.trt.Logger.WARNING)
        
        # Initialize TensorRT
        builder = self.trt.Builder(TRT_LOGGER)
        network = builder.create_network(1 << int(self.trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = self.trt.OnnxParser(network, TRT_LOGGER)
        
        # Parse ONNX model
        with open(onnx_path, "rb") as model:
            if not parser.parse(model.read()):
                for error in range(parser.num_errors):
                    logger.error(parser.get_error(error))
                raise RuntimeError("Failed to parse ONNX model")
        
        # Configure builder
        config = builder.create_builder_config()
        config.max_workspace_size = workspace_size
        
        if fp16_mode:
            config.set_flag(self.trt.BuilderFlag.FP16)
            logger.info("Enabled FP16 precision")
        
        if int8_mode:
            config.set_flag(self.trt.BuilderFlag.INT8)
            logger.info("Enabled INT8 precision")
        
        # Set optimization profile
        profile = builder.create_optimization_profile()
        input_tensor = network.get_input(0)
        input_shape = input_tensor.shape
        
        # Set min/opt/max shapes
        min_shape = [1, input_shape[1], input_shape[2], input_shape[3]]
        opt_shape = [max_batch_size, input_shape[1], input_shape[2], input_shape[3]]
        max_shape = [max_batch_size, input_shape[1], input_shape[2], input_shape[3]]
        
        profile.set_shape(input_tensor.name, min_shape, opt_shape, max_shape)
        config.add_optimization_profile(profile)
        
        # Build engine
        serialized_engine = builder.build_serialized_network(network, config)
        
        # Save engine
        with open(engine_path, "wb") as f:
            f.write(serialized_engine)
        
        logger.info(f"TensorRT engine built successfully: {engine_path}")
        return engine_path
    
    def optimize_for_jetson(
        self,
        model_path: str,
        output_prefix: str = "jetson_optimized",
        target_latency: float = 50.0
    ) -> dict:
        """
        Optimize model specifically for Jetson Nano
        
        Args:
            model_path: Path to the original model
            output_prefix: Prefix for output files
            target_latency: Target processing latency in ms
        
        Returns:
            Dictionary with paths to optimized models
        """
        results = {}
        
        # Step 1: Export to ONNX if not already
        if not model_path.endswith('.onnx'):
            onnx_path = self.export_to_onnx(model_path)
        else:
            onnx_path = model_path
        results['onnx'] = onnx_path
        
        # Step 2: Quantize to FP16 (best for Jetson)
        fp16_path = self.quantize_onnx(onnx_path, "fp16")
        results['fp16'] = fp16_path
        
        # Step 3: Try to build TensorRT engine
        if self.has_tensorrt:
            try:
                engine_path = self.optimize_for_tensorrt(
                    fp16_path,
                    fp16_mode=True,
                    int8_mode=False,
                    max_batch_size=1
                )
                results['tensorrt'] = engine_path
            except Exception as e:
                logger.warning(f"Failed to build TensorRT engine: {e}")
        
        # Step 4: Create optimized ONNX Runtime session options
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        # For Jetson, we want to use CUDA if available
        try:
            options.provider = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        except:
            options.provider = ['CPUExecutionProvider']
        
        results['session_options'] = options
        
        logger.info(f"Jetson optimization completed: {results}")
        return results
    
    def get_optimization_recommendations(
        self,
        device_type: str = "jetson_nano",
        target_fps: float = 30.0
    ) -> dict:
        """
        Get optimization recommendations for specific device
        
        Args:
            device_type: Device type (jetson_nano, jetson_xavier, aws_g5g, laptop_amd)
            target_fps: Target frames per second
        
        Returns:
            Dictionary with optimization recommendations
        """
        recommendations = {
            "model_size": "medium",
            "precision": "fp16",
            "batch_size": 1,
            "use_tensorrt": True,
            "use_quantization": True,
            "input_size": 640,
            "optimization_level": "high"
        }
        
        if device_type == "jetson_nano":
            recommendations.update({
                "model_size": "nano",
                "precision": "fp16",
                "batch_size": 1,
                "use_tensorrt": True,
                "input_size": 320,  # Smaller input for better performance
                "optimization_level": "aggressive"
            })
        elif device_type == "jetson_xavier":
            recommendations.update({
                "model_size": "small",
                "precision": "fp16",
                "batch_size": 2,
                "use_tensorrt": True,
                "input_size": 640,
                "optimization_level": "high"
            })
        elif device_type == "aws_g5g":
            recommendations.update({
                "model_size": "medium",
                "precision": "fp16",
                "batch_size": 4,
                "use_tensorrt": True,
                "input_size": 640,
                "optimization_level": "medium"
            })
        elif device_type == "laptop_amd":
            recommendations.update({
                "model_size": "medium",
                "precision": "fp32",  # No FP16 on AMD without ROCm
                "batch_size": 1,
                "use_tensorrt": False,
                "input_size": 640,
                "optimization_level": "medium"
            })
        
        # Adjust based on target FPS
        if target_fps > 60:
            recommendations["model_size"] = "nano"
            recommendations["input_size"] = 320
        elif target_fps > 30:
            recommendations["model_size"] = "small"
            recommendations["input_size"] = 480
        
        return recommendations
