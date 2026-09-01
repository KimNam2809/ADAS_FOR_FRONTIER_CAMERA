from __future__ import annotations

import ast
import logging
import json
import os
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import ConfigManager
from .signs import is_speed_limit_label, speed_value


LOGGER = logging.getLogger(__name__)


def _create_onnx_session(
    model_path: Path, runtime: str, optional_head: bool = False
) -> tuple[Any, str]:
    """Create a consistently bounded ORT session for every perception head."""
    import onnxruntime as ort

    available = ort.get_available_providers()
    if runtime in {"auto", "directml"} and "DmlExecutionProvider" in available:
        providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
    elif runtime in {"auto", "cuda"} and "CUDAExecutionProvider" in available:
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    else:
        providers = ["CPUExecutionProvider"]
    options = ort.SessionOptions()
    intra_key = (
        "ROADWATCH_ORT_OPTIONAL_INTRA_OP_NUM_THREADS"
        if optional_head
        else "ROADWATCH_ORT_INTRA_OP_NUM_THREADS"
    )
    inter_key = (
        "ROADWATCH_ORT_OPTIONAL_INTER_OP_NUM_THREADS"
        if optional_head
        else "ROADWATCH_ORT_INTER_OP_NUM_THREADS"
    )
    intra_threads = int(
        os.getenv(intra_key, os.getenv("ROADWATCH_ORT_INTRA_OP_NUM_THREADS", "0"))
    )
    inter_threads = int(
        os.getenv(inter_key, os.getenv("ROADWATCH_ORT_INTER_OP_NUM_THREADS", "0"))
    )
    if intra_threads > 0:
        options.intra_op_num_threads = intra_threads
    if inter_threads > 0:
        options.inter_op_num_threads = inter_threads
    session = ort.InferenceSession(
        str(model_path), sess_options=options, providers=providers
    )
    return session, session.get_providers()[0]


def _parse_model_names(value: str | None) -> dict[int, str]:
    """Parse Ultralytics ONNX names metadata (Python repr or JSON)."""
    if not value:
        return {}
    parsed: Any
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return {}
    if isinstance(parsed, list):
        return {index: str(label) for index, label in enumerate(parsed)}
    if isinstance(parsed, dict):
        try:
            return {int(key): str(label) for key, label in parsed.items()}
        except (TypeError, ValueError):
            return {}
    return {}


class UltralyticsDetector:
    def __init__(
        self,
        model_path: Path,
        confidence: float,
        image_size: int,
        device: str = "cpu",
        allowed_classes: list[int] | None = None,
        class_thresholds: dict[str, float] | None = None,
    ) -> None:
        self.model_path = model_path
        self.confidence = confidence
        self.image_size = image_size
        self.device = device
        self.allowed_classes = allowed_classes
        self.class_thresholds = class_thresholds or {}
        self.model: Any | None = None
        self.error: str | None = None
        self.names: dict[int, str] = {}

    def load(self) -> None:
        if self.model is not None or self.error:
            return
        try:
            from ultralytics import YOLO

            self.model = YOLO(str(self.model_path))
            self.names = {int(k): str(v) for k, v in self.model.names.items()}
        except Exception as exc:  # pragma: no cover - hardware/runtime dependent
            self.error = str(exc)
            LOGGER.exception("Không thể tải model %s", self.model_path.name)

    def infer(self, frame: np.ndarray) -> tuple[list[dict[str, Any]], float]:
        self.load()
        if self.model is None:
            return [], 0.0
        started = time.perf_counter()
        try:
            results = self.model.predict(
                source=frame,
                conf=self.confidence,
                imgsz=self.image_size,
                classes=self.allowed_classes,
                device=self.device,
                verbose=False,
            )
            detections: list[dict[str, Any]] = []
            if results:
                boxes = results[0].boxes
                if boxes is not None:
                    for xyxy, confidence, class_id in zip(
                        boxes.xyxy.cpu().numpy(),
                        boxes.conf.cpu().numpy(),
                        boxes.cls.cpu().numpy(),
                    ):
                        cid = int(class_id)
                        label = self.names.get(cid, str(cid))
                        if float(confidence) < float(
                            self.class_thresholds.get(label, self.confidence)
                        ):
                            continue
                        detections.append(
                            {
                                "bbox": [round(float(v), 2) for v in xyxy],
                                "class_id": cid,
                                "label": label,
                                "confidence": round(float(confidence), 4),
                            }
                        )
            return detections, (time.perf_counter() - started) * 1000
        except Exception as exc:  # pragma: no cover - hardware/runtime dependent
            self.error = str(exc)
            LOGGER.exception("Suy luận thất bại với %s", self.model_path.name)
            return [], (time.perf_counter() - started) * 1000

    def status(self) -> dict[str, Any]:
        return {
            "model": self.model_path.name,
            "available": self.model_path.exists(),
            "loaded": self.model is not None,
            "provider": f"Ultralytics/{self.device}",
            "error": self.error,
        }


class OnnxYoloDetector:
    """Ultralytics YOLO ONNX adapter with DirectML/CUDA/CPU provider selection."""

    def __init__(
        self,
        model_path: Path,
        confidence: float,
        image_size: int,
        runtime: str = "auto",
        allowed_classes: list[int] | None = None,
        class_thresholds: dict[str, float] | None = None,
        optional_head: bool = False,
    ) -> None:
        self.model_path = model_path
        self.confidence = confidence
        self.image_size = image_size
        self.runtime = runtime
        self.allowed_classes = allowed_classes
        self.class_thresholds = class_thresholds or {}
        self.optional_head = optional_head
        self.session: Any | None = None
        self.provider = "unavailable"
        self.error: str | None = None
        self.input_width = image_size
        self.input_height = image_size
        names_path = model_path.with_suffix(".names.json")
        self.names = (
            {int(key): str(value) for key, value in json.loads(names_path.read_text(encoding="utf-8")).items()}
            if names_path.exists()
            else {}
        )

    def load(self) -> None:
        if self.session is not None or self.error:
            return
        try:
            self.session, self.provider = _create_onnx_session(
                self.model_path, self.runtime, self.optional_head
            )
            input_shape = self.session.get_inputs()[0].shape
            if len(input_shape) >= 4:
                if isinstance(input_shape[2], int):
                    self.input_height = int(input_shape[2])
                if isinstance(input_shape[3], int):
                    self.input_width = int(input_shape[3])
            if not self.names:
                metadata = self.session.get_modelmeta().custom_metadata_map
                self.names = _parse_model_names(metadata.get("names"))
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.error = str(exc)
            LOGGER.exception("Không thể tải YOLO ONNX %s", self.model_path.name)

    def infer(self, frame: np.ndarray) -> tuple[list[dict[str, Any]], float]:
        self.load()
        if self.session is None:
            return [], 0.0
        started = time.perf_counter()
        try:
            height, width = frame.shape[:2]
            scale = min(self.input_width / width, self.input_height / height)
            resized_w, resized_h = int(round(width * scale)), int(round(height * scale))
            resized = cv2.resize(frame, (resized_w, resized_h), interpolation=cv2.INTER_LINEAR)
            pad_x = (self.input_width - resized_w) // 2
            pad_y = (self.input_height - resized_h) // 2
            canvas = np.full((self.input_height, self.input_width, 3), 114, dtype=np.uint8)
            canvas[pad_y:pad_y + resized_h, pad_x:pad_x + resized_w] = resized
            rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            tensor = np.transpose(rgb, (2, 0, 1))[None]
            raw = self.session.run(None, {self.session.get_inputs()[0].name: tensor})[0]
            predictions = raw[0]

            # YOLO26 exports its end-to-end, NMS-free head as
            # [num_detections, 6] = [x1, y1, x2, y2, confidence, class_id].
            # YOLO11 and older Ultralytics exports keep the raw
            # [4 + num_classes, num_anchors] layout below.  Detect the
            # contract from the tensor rather than from the filename so the
            # adapter remains safe for both formats.
            end_to_end = predictions.ndim == 2 and predictions.shape[1] == 6
            if end_to_end:
                boxes_xyxy = predictions[:, :4]
                confidences = predictions[:, 4]
                class_ids = np.rint(predictions[:, 5]).astype(np.int64)
                class_scores = np.zeros(
                    (len(predictions), max(len(self.names), int(class_ids.max()) + 1 if len(class_ids) else 1)),
                    dtype=np.float32,
                )
                if len(predictions):
                    class_scores[np.arange(len(predictions)), class_ids] = confidences
            else:
                if predictions.shape[0] < predictions.shape[1]:
                    predictions = predictions.T
                class_scores = predictions[:, 4:]
                class_ids = np.argmax(class_scores, axis=1)
                confidences = class_scores[np.arange(len(class_ids)), class_ids]
                boxes_xywh = predictions[:, :4]

            keep = confidences >= self.confidence
            if self.allowed_classes is not None:
                keep &= np.isin(class_ids, np.asarray(self.allowed_classes))
            if end_to_end:
                boxes_xyxy = boxes_xyxy[keep]
            else:
                boxes_xywh = boxes_xywh[keep]
            confidences = confidences[keep]
            class_ids = class_ids[keep]
            kept_class_scores = class_scores[keep]
            if self.class_thresholds:
                threshold_keep = np.asarray(
                    [
                        float(confidence)
                        >= float(
                            self.class_thresholds.get(
                                self.names.get(int(class_id), str(int(class_id))),
                                self.confidence,
                            )
                        )
                        for confidence, class_id in zip(confidences, class_ids)
                    ],
                    dtype=bool,
                )
                if end_to_end:
                    boxes_xyxy = boxes_xyxy[threshold_keep]
                else:
                    boxes_xywh = boxes_xywh[threshold_keep]
                confidences = confidences[threshold_keep]
                class_ids = class_ids[threshold_keep]
                kept_class_scores = kept_class_scores[threshold_keep]
            nms_boxes: list[list[float]] = []
            if end_to_end:
                for x1, y1, x2, y2 in boxes_xyxy:
                    nms_boxes.append(
                        [float(x1), float(y1), float(x2 - x1), float(y2 - y1)]
                    )
            else:
                for cx, cy, bw, bh in boxes_xywh:
                    nms_boxes.append(
                        [float(cx - bw / 2), float(cy - bh / 2), float(bw), float(bh)]
                    )
            indices = cv2.dnn.NMSBoxes(nms_boxes, confidences.tolist(), self.confidence, 0.45)
            detections: list[dict[str, Any]] = []
            for index in np.asarray(indices).reshape(-1).tolist() if len(indices) else []:
                x, y, bw, bh = nms_boxes[index]
                x1 = max(0.0, (x - pad_x) / scale)
                y1 = max(0.0, (y - pad_y) / scale)
                x2 = min(float(width), (x + bw - pad_x) / scale)
                y2 = min(float(height), (y + bh - pad_y) / scale)
                class_id = int(class_ids[index])
                if end_to_end:
                    alternatives = [
                        {
                            "class_id": class_id,
                            "label": self.names.get(class_id, str(class_id)),
                            "confidence": round(float(confidences[index]), 4),
                        }
                    ]
                else:
                    top_indices = np.argsort(kept_class_scores[index])[-3:][::-1]
                    alternatives = [
                        {
                            "class_id": int(alt_id),
                            "label": self.names.get(int(alt_id), str(int(alt_id))),
                            "confidence": round(
                                float(kept_class_scores[index][alt_id]), 4
                            ),
                        }
                        for alt_id in top_indices
                    ]
                detections.append(
                    {
                        "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                        "class_id": class_id,
                        "label": self.names.get(class_id, str(class_id)),
                        "confidence": round(float(confidences[index]), 4),
                        "alternatives": alternatives,
                    }
                )
            return detections, (time.perf_counter() - started) * 1000
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.error = str(exc)
            LOGGER.exception("Suy luận YOLO ONNX thất bại: %s", self.model_path.name)
            return [], (time.perf_counter() - started) * 1000

    def status(self) -> dict[str, Any]:
        return {
            "model": self.model_path.name,
            "available": self.model_path.exists(),
            "loaded": self.session is not None,
            "provider": f"ONNX/{self.provider}",
            "input_size": f"{self.input_width}x{self.input_height}",
            "error": self.error,
        }


class SpeedValueClassifier:
    """Optional second-stage classifier for the digits inside a speed sign."""

    def __init__(self, model_path: Path, confidence: float, device: str = "cpu") -> None:
        self.model_path = model_path
        self.confidence = confidence
        self.device = device
        self.model: Any | None = None
        self.session: Any | None = None
        self.names: dict[int, str] = {}
        self.provider = "unavailable"
        self.error: str | None = None

    def load(self) -> None:
        if self.model is not None or self.session is not None or self.error or not self.model_path.exists():
            return
        try:
            if self.model_path.suffix.lower() == ".onnx":
                self.session, self.provider = _create_onnx_session(
                    self.model_path, self.device, True
                )
                metadata = self.session.get_modelmeta().custom_metadata_map
                self.names = _parse_model_names(metadata.get("names"))
            else:
                from ultralytics import YOLO

                self.model = YOLO(str(self.model_path))
                self.provider = f"Ultralytics/{self.device}"
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.error = str(exc)
            LOGGER.exception("Không thể tải speed-value classifier")

    def classify(self, crops: list[np.ndarray]) -> list[tuple[int | None, float]]:
        self.load()
        if (self.model is None and self.session is None) or not crops:
            return [(None, 0.0) for _ in crops]
        try:
            if self.session is not None:
                resolved: list[tuple[int | None, float]] = []
                input_name = self.session.get_inputs()[0].name
                for crop in crops:
                    resized = cv2.resize(crop, (160, 160), interpolation=cv2.INTER_LINEAR)
                    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                    tensor = np.transpose(rgb, (2, 0, 1))[None]
                    probabilities = self.session.run(None, {input_name: tensor})[0][0]
                    class_id = int(np.argmax(probabilities))
                    confidence = float(probabilities[class_id])
                    value = speed_value(self.names.get(class_id, str(class_id)))
                    resolved.append(
                        (value, confidence)
                        if value is not None and confidence >= self.confidence
                        else (None, confidence)
                    )
                return resolved
            predictions = self.model.predict(crops, imgsz=160, device=self.device, verbose=False)
            resolved: list[tuple[int | None, float]] = []
            for prediction in predictions:
                probs = prediction.probs
                if probs is None:
                    resolved.append((None, 0.0))
                    continue
                class_id = int(probs.top1)
                confidence = float(probs.top1conf.cpu().item())
                label = str(prediction.names[class_id])
                value = speed_value(label)
                resolved.append(
                    (value, confidence) if value is not None and confidence >= self.confidence else (None, confidence)
                )
            return resolved
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.error = str(exc)
            LOGGER.exception("Speed-value classification failed")
            return [(None, 0.0) for _ in crops]

    def status(self) -> dict[str, Any]:
        return {
            "model": self.model_path.name,
            "available": self.model_path.exists(),
            "loaded": self.model is not None or self.session is not None,
            "provider": self.provider,
            "error": self.error,
        }


class TrafficSignEnsemble:
    """Detector plus optional crop classifier; keeps the detector as fallback."""

    def __init__(self, detector: Any, classifier: SpeedValueClassifier) -> None:
        self.detector = detector
        self.classifier = classifier

    def load(self) -> None:
        self.detector.load()
        self.classifier.load()

    def infer(self, frame: np.ndarray) -> tuple[list[dict[str, Any]], float]:
        detections, latency = self.detector.infer(frame)
        speed_indices: list[int] = []
        crops: list[np.ndarray] = []
        height, width = frame.shape[:2]
        for index, detection in enumerate(detections):
            if not is_speed_limit_label(str(detection["label"])):
                continue
            x1, y1, x2, y2 = detection["bbox"]
            pad_x = max(2, int((x2 - x1) * 0.12))
            pad_y = max(2, int((y2 - y1) * 0.12))
            crop = frame[
                max(0, int(y1) - pad_y) : min(height, int(y2) + pad_y),
                max(0, int(x1) - pad_x) : min(width, int(x2) + pad_x),
            ]
            if crop.size:
                speed_indices.append(index)
                crops.append(crop)
        started = time.perf_counter()
        for index, (value, confidence) in zip(speed_indices, self.classifier.classify(crops)):
            detections[index]["speed_classifier_confidence"] = round(confidence, 4)
            if value is None:
                continue
            detections[index]["detector_label"] = detections[index]["label"]
            detections[index]["detector_class_id"] = detections[index]["class_id"]
            detections[index]["label"] = str(value)
            detections[index]["class_id"] = 10_000 + value
            detections[index]["speed_value_source"] = "crop_classifier"
        return detections, latency + (time.perf_counter() - started) * 1000

    def status(self) -> dict[str, Any]:
        status = self.detector.status()
        status["speed_classifier"] = self.classifier.status()
        return status


class YOLOPSegmenter:
    IMAGENET_MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
    IMAGENET_STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)

    def __init__(self, model_path: Path, runtime: str = "auto") -> None:
        self.model_path = model_path
        self.runtime = runtime
        self.session: Any | None = None
        self.provider = "unavailable"
        self.error: str | None = None

    def load(self) -> None:
        if self.session is not None or self.error:
            return
        try:
            self.session, self.provider = _create_onnx_session(
                self.model_path, self.runtime, True
            )
        except Exception as exc:  # pragma: no cover - hardware/runtime dependent
            self.error = str(exc)
            LOGGER.exception("Không thể tải YOLOP ONNX")

    def infer(self, frame: np.ndarray) -> tuple[dict[str, Any], float]:
        self.load()
        if self.session is None:
            return self.empty(frame.shape[:2]), 0.0
        started = time.perf_counter()
        try:
            height, width = frame.shape[:2]
            resized = cv2.resize(frame, (640, 640), interpolation=cv2.INTER_LINEAR)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            normalized = (rgb - self.IMAGENET_MEAN) / self.IMAGENET_STD
            tensor = np.transpose(normalized, (2, 0, 1))[None].astype(np.float32)
            outputs = self.session.run(None, {self.session.get_inputs()[0].name: tensor})
            drive = np.argmax(outputs[1][0], axis=0).astype(np.uint8)
            lane = np.argmax(outputs[2][0], axis=0).astype(np.uint8)
            drive = cv2.resize(drive, (width, height), interpolation=cv2.INTER_NEAREST)
            lane = cv2.resize(lane, (width, height), interpolation=cv2.INTER_NEAREST)
            lane_pixels = int(np.count_nonzero(lane))
            lower_lane_pixels = int(np.count_nonzero(lane[int(height * 0.45) :]))
            quality = min(1.0, lower_lane_pixels / max(width * height * 0.008, 1))
            return {
                "lane_mask": lane,
                "drivable_mask": drive,
                "quality": round(float(quality), 4),
                "lane_pixels": lane_pixels,
                "provider": self.provider,
            }, (time.perf_counter() - started) * 1000
        except Exception as exc:  # pragma: no cover - hardware/runtime dependent
            self.error = str(exc)
            LOGGER.exception("Suy luận YOLOP thất bại")
            return self.empty(frame.shape[:2]), (time.perf_counter() - started) * 1000

    def empty(self, shape: tuple[int, int]) -> dict[str, Any]:
        return {
            "lane_mask": np.zeros(shape, dtype=np.uint8),
            "drivable_mask": np.zeros(shape, dtype=np.uint8),
            "quality": 0.0,
            "lane_pixels": 0,
            "provider": self.provider,
        }

    def status(self) -> dict[str, Any]:
        return {
            "model": self.model_path.name,
            "available": self.model_path.exists(),
            "loaded": self.session is not None,
            "provider": self.provider,
            "error": self.error,
        }


class TwinLiteNetPlusSegmenter:
    """Static ONNX adapter for the TwinLiteNet+ lane/drivable candidate."""

    INPUT_WIDTH = 640
    INPUT_HEIGHT = 384

    def __init__(self, model_path: Path, runtime: str = "auto") -> None:
        self.model_path = model_path
        self.runtime = runtime
        self.session: Any | None = None
        self.provider = "unavailable"
        self.error: str | None = None
        self.input_name: str | None = None
        self.input_shape: list[int] | None = None

    @staticmethod
    def _letterbox(
        image: np.ndarray,
    ) -> tuple[np.ndarray, tuple[float, float]]:
        height, width = image.shape[:2]
        ratio = min(
            TwinLiteNetPlusSegmenter.INPUT_HEIGHT / height,
            TwinLiteNetPlusSegmenter.INPUT_WIDTH / width,
        )
        new_width = int(round(width * ratio))
        new_height = int(round(height * ratio))
        pad_width = TwinLiteNetPlusSegmenter.INPUT_WIDTH - new_width
        pad_height = TwinLiteNetPlusSegmenter.INPUT_HEIGHT - new_height
        # The upstream implementation constrains padding to the network stride.
        pad_width = float(np.mod(pad_width, 32)) / 2.0
        pad_height = float(np.mod(pad_height, 32)) / 2.0
        if (width, height) != (new_width, new_height):
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        top = int(round(pad_height - 0.1))
        bottom = int(round(pad_height + 0.1))
        left = int(round(pad_width - 0.1))
        right = int(round(pad_width + 0.1))
        image = cv2.copyMakeBorder(
            image,
            top,
            bottom,
            left,
            right,
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114),
        )
        return image, (pad_width, pad_height)

    def load(self) -> None:
        if self.session is not None or self.error:
            return
        if not self.model_path.exists():
            self.error = f"Không tìm thấy TwinLiteNet+ ONNX: {self.model_path.name}"
            return
        try:
            self.session, self.provider = _create_onnx_session(
                self.model_path, self.runtime, False
            )
            input_meta = self.session.get_inputs()[0]
            shape = list(input_meta.shape)
            if len(shape) != 4 or any(not isinstance(value, int) for value in shape):
                raise ValueError(f"TwinLiteNet+ cần input tĩnh NCHW, nhận {shape}")
            if shape != [1, 3, self.INPUT_HEIGHT, self.INPUT_WIDTH]:
                raise ValueError(
                    "TwinLiteNet+ input không đúng contract "
                    f"[1,3,{self.INPUT_HEIGHT},{self.INPUT_WIDTH}], nhận {shape}"
                )
            self.input_name = input_meta.name
            self.input_shape = [int(value) for value in shape]
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.error = str(exc)
            self.session = None
            LOGGER.exception("Không thể tải TwinLiteNet+ ONNX")

    def infer(self, frame: np.ndarray) -> tuple[dict[str, Any], float]:
        self.load()
        if self.session is None or self.input_name is None:
            return self.empty(frame.shape[:2]), 0.0
        started = time.perf_counter()
        height, width = frame.shape[:2]
        try:
            padded, (pad_width, pad_height) = self._letterbox(frame)
            rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            tensor = np.transpose(rgb, (2, 0, 1))[None].astype(np.float32)
            raw_outputs = self.session.run(None, {self.input_name: tensor})
            if len(raw_outputs) < 2:
                raise ValueError(f"TwinLiteNet+ trả về {len(raw_outputs)} output, cần 2")
            output_names = [item.name.lower() for item in self.session.get_outputs()]
            output_map = dict(zip(output_names, raw_outputs))
            drive_logits = next(
                (value for name, value in output_map.items() if "drivable" in name or "drive" in name),
                raw_outputs[0],
            )
            lane_logits = next(
                (value for name, value in output_map.items() if "lane" in name),
                raw_outputs[1],
            )
            drive = np.argmax(drive_logits[0], axis=0).astype(np.uint8)
            lane = np.argmax(lane_logits[0], axis=0).astype(np.uint8)
            output_height, output_width = drive.shape[:2]
            crop_left = int(round(pad_width))
            crop_top = int(round(pad_height))
            crop_right = output_width - crop_left
            crop_bottom = output_height - crop_top
            drive = drive[crop_top:crop_bottom, crop_left:crop_right]
            lane = lane[crop_top:crop_bottom, crop_left:crop_right]
            drive = cv2.resize(drive, (width, height), interpolation=cv2.INTER_NEAREST)
            lane = cv2.resize(lane, (width, height), interpolation=cv2.INTER_NEAREST)
            lane_pixels = int(np.count_nonzero(lane))
            lower_lane_pixels = int(np.count_nonzero(lane[int(height * 0.45) :]))
            quality = min(1.0, lower_lane_pixels / max(width * height * 0.008, 1))
            return {
                "lane_mask": lane,
                "drivable_mask": drive,
                "quality": round(float(quality), 4),
                "lane_pixels": lane_pixels,
                "drivable_pixels": int(np.count_nonzero(drive)),
                "provider": self.provider,
                "source": "twinlitenetplus",
                "fallback_used": False,
            }, (time.perf_counter() - started) * 1000
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.error = str(exc)
            LOGGER.exception("Suy luận TwinLiteNet+ thất bại")
            return self.empty(frame.shape[:2]), (time.perf_counter() - started) * 1000

    def empty(self, shape: tuple[int, int]) -> dict[str, Any]:
        return {
            "lane_mask": np.zeros(shape, dtype=np.uint8),
            "drivable_mask": np.zeros(shape, dtype=np.uint8),
            "quality": 0.0,
            "lane_pixels": 0,
            "drivable_pixels": 0,
            "provider": self.provider,
            "source": "twinlitenetplus",
            "fallback_used": False,
        }

    def status(self) -> dict[str, Any]:
        return {
            "model": self.model_path.name,
            "available": self.model_path.exists(),
            "loaded": self.session is not None,
            "provider": self.provider,
            "input_shape": self.input_shape,
            "error": self.error,
        }


class FallbackLaneSegmenter:
    """Run TwinLiteNet+ as primary and use YOLOP on candidate failure."""

    def __init__(self, primary: TwinLiteNetPlusSegmenter, fallback: YOLOPSegmenter) -> None:
        self.primary = primary
        self.fallback = fallback
        self.fallback_count = 0
        self.last_fallback_reason: str | None = None

    def load(self) -> None:
        # Load both at startup so a failure does not add cold-start latency to a warning.
        self.primary.load()
        self.fallback.load()

    def infer(self, frame: np.ndarray) -> tuple[dict[str, Any], float]:
        primary_output, primary_ms = self.primary.infer(frame)
        reason: str | None = None
        if self.primary.error:
            reason = "twinlitenetplus_error"
        elif primary_output.get("lane_mask") is None:
            reason = "twinlitenetplus_missing_lane_mask"
        elif int(primary_output.get("lane_pixels", 0)) <= 0:
            reason = "twinlitenetplus_empty_lane_mask"

        if reason is None:
            primary_output["source"] = "twinlitenetplus"
            primary_output["fallback_used"] = False
            return primary_output, primary_ms

        fallback_output, fallback_ms = self.fallback.infer(frame)
        self.fallback_count += 1
        self.last_fallback_reason = reason
        fallback_output["source"] = "yolop_fallback"
        fallback_output["fallback_used"] = True
        fallback_output["fallback_reason"] = reason
        fallback_output["primary_model"] = self.primary.model_path.name
        return fallback_output, primary_ms + fallback_ms

    def empty(self, shape: tuple[int, int]) -> dict[str, Any]:
        output = self.fallback.empty(shape)
        output["source"] = "yolop_fallback"
        output["fallback_used"] = True
        output["fallback_reason"] = "empty_request"
        return output

    def status(self) -> dict[str, Any]:
        primary_loaded = self.primary.session is not None
        fallback_loaded = self.fallback.session is not None
        if primary_loaded and not self.primary.error:
            active_model = "twinlitenetplus"
        elif fallback_loaded:
            active_model = "yolop_fallback"
        else:
            active_model = "unavailable"
        return {
            "model": "TwinLiteNet+ primary -> YOLOP fallback",
            "available": self.primary.model_path.exists() or self.fallback.model_path.exists(),
            "loaded": primary_loaded or fallback_loaded,
            "active_model": active_model,
            "primary_loaded": primary_loaded,
            "fallback_loaded": fallback_loaded,
            "provider": f"primary={self.primary.provider}; fallback={self.fallback.provider}",
            "primary": self.primary.status(),
            "fallback": self.fallback.status(),
            "fallback_count": self.fallback_count,
            "last_fallback_reason": self.last_fallback_reason,
        }


class UFLDv2LaneDetector:
    """ONNX adapter for the official UFLDv2 CULane ResNet-18 checkpoint."""

    IMAGENET_MEAN = YOLOPSegmenter.IMAGENET_MEAN
    IMAGENET_STD = YOLOPSegmenter.IMAGENET_STD
    INPUT_WIDTH = 1600
    INPUT_HEIGHT = 320
    RESIZE_HEIGHT = round(INPUT_HEIGHT / 0.6)

    def __init__(self, model_path: Path, runtime: str = "auto") -> None:
        self.model_path = model_path
        self.runtime = runtime
        self.session: Any | None = None
        self.provider = "unavailable"
        self.error: str | None = None

    def load(self) -> None:
        if self.session is not None or self.error:
            return
        try:
            self.session, self.provider = _create_onnx_session(
                self.model_path, self.runtime, True
            )
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.error = str(exc)
            LOGGER.exception("Không thể tải UFLDv2 ONNX")

    @staticmethod
    def _softmax(values: np.ndarray) -> np.ndarray:
        shifted = values - np.max(values)
        exp = np.exp(shifted)
        return exp / max(float(np.sum(exp)), 1e-9)

    @classmethod
    def decode(
        cls,
        outputs: dict[str, np.ndarray],
        image_width: int,
        image_height: int,
        local_width: int = 1,
    ) -> list[dict[str, Any]]:
        loc_row = outputs["loc_row"]
        loc_col = outputs["loc_col"]
        exist_row = outputs["exist_row"]
        exist_col = outputs["exist_col"]
        num_grid_row, num_cls_row, _ = loc_row.shape[1:]
        num_grid_col, num_cls_col, _ = loc_col.shape[1:]
        row_anchor = np.linspace(0.42, 1.0, num_cls_row)
        col_anchor = np.linspace(0.0, 1.0, num_cls_col)
        valid_row = np.argmax(exist_row, axis=1)[0]
        valid_col = np.argmax(exist_col, axis=1)[0]
        max_row = np.argmax(loc_row, axis=1)[0]
        max_col = np.argmax(loc_col, axis=1)[0]
        lanes: list[dict[str, Any]] = []

        for lane_id in (1, 2):
            points: list[list[int]] = []
            if int(np.sum(valid_row[:, lane_id])) > num_cls_row / 2:
                for anchor_id in range(num_cls_row):
                    if not valid_row[anchor_id, lane_id]:
                        continue
                    center = int(max_row[anchor_id, lane_id])
                    indexes = np.arange(
                        max(0, center - local_width),
                        min(num_grid_row - 1, center + local_width) + 1,
                    )
                    weights = cls._softmax(loc_row[0, indexes, anchor_id, lane_id])
                    position = float(np.sum(weights * indexes) + 0.5)
                    points.append(
                        [
                            round(position / (num_grid_row - 1) * image_width),
                            round(row_anchor[anchor_id] * image_height),
                        ]
                    )
            lanes.append({"lane_id": lane_id, "role": "ego_boundary", "points": points})

        for lane_id in (0, 3):
            points = []
            if int(np.sum(valid_col[:, lane_id])) > num_cls_col / 4:
                for anchor_id in range(num_cls_col):
                    if not valid_col[anchor_id, lane_id]:
                        continue
                    center = int(max_col[anchor_id, lane_id])
                    indexes = np.arange(
                        max(0, center - local_width),
                        min(num_grid_col - 1, center + local_width) + 1,
                    )
                    weights = cls._softmax(loc_col[0, indexes, anchor_id, lane_id])
                    position = float(np.sum(weights * indexes) + 0.5)
                    points.append(
                        [
                            round(col_anchor[anchor_id] * image_width),
                            round(position / (num_grid_col - 1) * image_height),
                        ]
                    )
            lanes.append({"lane_id": lane_id, "role": "side_boundary", "points": points})
        return lanes

    def infer(self, frame: np.ndarray) -> tuple[dict[str, Any], float]:
        self.load()
        height, width = frame.shape[:2]
        if self.session is None:
            return self.empty((height, width)), 0.0
        started = time.perf_counter()
        try:
            resized = cv2.resize(
                frame, (self.INPUT_WIDTH, self.RESIZE_HEIGHT), interpolation=cv2.INTER_LINEAR
            )
            cropped = resized[-self.INPUT_HEIGHT :, :, :]
            rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            normalized = (rgb - self.IMAGENET_MEAN) / self.IMAGENET_STD
            tensor = np.transpose(normalized, (2, 0, 1))[None].astype(np.float32)
            raw = self.session.run(None, {self.session.get_inputs()[0].name: tensor})
            names = [item.name for item in self.session.get_outputs()]
            lanes = self.decode(dict(zip(names, raw)), width, height)
            ego_lanes = [lane for lane in lanes if lane["role"] == "ego_boundary"]
            mask = np.zeros((height, width), dtype=np.uint8)
            for lane in ego_lanes:
                points = np.asarray(lane["points"], dtype=np.int32)
                if len(points) >= 2:
                    cv2.polylines(mask, [points], False, 1, thickness=max(2, width // 480))
            valid_ego = sum(len(lane["points"]) >= 20 for lane in ego_lanes)
            point_coverage = min(
                1.0,
                sum(len(lane["points"]) for lane in ego_lanes) / (2 * 72),
            )
            quality = point_coverage if valid_ego == 2 else point_coverage * 0.35
            return {
                "lane_mask": mask,
                "drivable_mask": np.zeros((height, width), dtype=np.uint8),
                "quality": round(float(quality), 4),
                "lane_pixels": int(np.count_nonzero(mask)),
                "lane_count": sum(len(lane["points"]) >= 2 for lane in lanes),
                "lane_instances": lanes,
                "provider": self.provider,
                "source": "ufldv2",
            }, (time.perf_counter() - started) * 1000
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.error = str(exc)
            LOGGER.exception("Suy luận UFLDv2 thất bại")
            return self.empty((height, width)), (time.perf_counter() - started) * 1000

    def empty(self, shape: tuple[int, int]) -> dict[str, Any]:
        return {
            "lane_mask": np.zeros(shape, dtype=np.uint8),
            "drivable_mask": np.zeros(shape, dtype=np.uint8),
            "quality": 0.0,
            "lane_pixels": 0,
            "lane_count": 0,
            "lane_instances": [],
            "provider": self.provider,
            "source": "ufldv2",
        }

    def status(self) -> dict[str, Any]:
        return {
            "model": self.model_path.name,
            "available": self.model_path.exists(),
            "loaded": self.session is not None,
            "provider": self.provider,
            "error": self.error,
        }


class FusedLaneSegmenter:
    """Use UFLDv2 geometry with YOLOP's drivable-area output and safe fallback."""

    def __init__(
        self,
        yolop: YOLOPSegmenter,
        ufldv2: UFLDv2LaneDetector,
        drivable_interval: int = 4,
    ) -> None:
        self.yolop = yolop
        self.ufldv2 = ufldv2
        self.drivable_interval = max(1, int(drivable_interval))
        self._calls = 0
        self._cached_yolop: dict[str, Any] | None = None

    def load(self) -> None:
        self.yolop.load()
        self.ufldv2.load()

    def infer(self, frame: np.ndarray) -> tuple[dict[str, Any], float]:
        self._calls += 1
        yolop_ms = 0.0
        if self._cached_yolop is None or self._calls % self.drivable_interval == 1:
            self._cached_yolop, yolop_ms = self.yolop.infer(frame)
        yolop_output = self._cached_yolop
        if yolop_output is None:
            yolop_output = self.yolop.empty(frame.shape[:2])
        ufld_output, ufld_ms = self.ufldv2.infer(frame)
        if ufld_output["quality"] >= 0.48:
            ufld_output["drivable_mask"] = yolop_output["drivable_mask"]
            ufld_output["source"] = "ufldv2+yolop_drivable"
            return ufld_output, yolop_ms + ufld_ms
        if self.ufldv2.error:
            yolop_output["source"] = "yolop_runtime_fallback"
            yolop_output["ufldv2_quality"] = ufld_output["quality"]
            return yolop_output, yolop_ms + ufld_ms
        # Low light and compression can make both models hallucinate lane
        # fragments. If the stronger geometry model rejects the frame, retain
        # only YOLOP's drivable area and suppress LDW rather than trust a noisy
        # lane mask.
        ufld_output["drivable_mask"] = yolop_output["drivable_mask"]
        ufld_output["source"] = "ufldv2_degraded_drivable_only"
        return ufld_output, yolop_ms + ufld_ms

    def empty(self, shape: tuple[int, int]) -> dict[str, Any]:
        return self.yolop.empty(shape)

    def status(self) -> dict[str, Any]:
        return {
            "model": "UFLDv2 lane + YOLOP drivable",
            "available": self.yolop.model_path.exists() and self.ufldv2.model_path.exists(),
            "loaded": self.yolop.session is not None and self.ufldv2.session is not None,
            "provider": f"lane={self.ufldv2.provider}; drivable={self.yolop.provider}",
            "error": self.ufldv2.error or self.yolop.error,
        }


class PerceptionEngine:
    def __init__(self, config: dict[str, Any]) -> None:
        inf = config["inference"]
        self.config = inf
        object_profile_name = str(inf.get("object_profile", "baseline_coco"))
        object_profile = inf.get("object_profiles", {}).get(object_profile_name, {})
        object_pt = ConfigManager.model_path(
            str(object_profile.get("model", inf.get("object_model", "yolo11n.pt")))
        )
        object_onnx = ConfigManager.model_path(
            str(object_profile.get("onnx_model", inf.get("object_onnx_model", "yolo11n.onnx")))
        )
        sign_pt = ConfigManager.model_path(
            str(inf.get("sign_model", "yolo11s_vietnam_traffic.pt"))
        )
        sign_onnx = ConfigManager.model_path(
            str(inf.get("sign_onnx_model", "yolo11s_vietnam_traffic.onnx"))
        )
        prefer_onnx = bool(inf.get("prefer_onnx_detectors", False))
        road_user_classes = [
            int(v)
            for v in object_profile.get("road_user_classes", inf["road_user_classes"])
        ]
        class_thresholds = {
            str(key): float(value)
            for key, value in object_profile.get("class_confidence", {}).items()
        }
        detector_args = (float(inf["object_confidence"]), int(inf["image_size"]))
        self.objects = (
            OnnxYoloDetector(
                object_onnx,
                *detector_args,
                str(inf.get("runtime", "auto")),
                road_user_classes,
                class_thresholds,
            )
            if prefer_onnx and object_onnx.exists()
            else UltralyticsDetector(
                object_pt,
                *detector_args,
                str(inf.get("device", "cpu")),
                road_user_classes,
                class_thresholds,
            )
        )
        sign_detector = (
            OnnxYoloDetector(
                sign_onnx,
                float(inf["sign_confidence"]),
                int(inf["image_size"]),
                str(inf.get("runtime", "auto")),
                optional_head=True,
            )
            if prefer_onnx and sign_onnx.exists()
            else UltralyticsDetector(
                sign_pt,
                float(inf["sign_confidence"]),
                int(inf["image_size"]),
                str(inf.get("device", "cpu")),
            )
        )
        self.signs = TrafficSignEnsemble(
            sign_detector,
            SpeedValueClassifier(
                ConfigManager.model_path(
                    str(inf.get("speed_classifier_model", "roadwatch_speed_digits_v2.pt"))
                ),
                float(inf.get("speed_classifier_confidence", 0.95)),
                str(inf.get("device", "cpu")),
            ),
        )
        runtime = str(inf.get("runtime", "auto"))
        yolop = YOLOPSegmenter(
            ConfigManager.model_path("yolop_lane_detection_640.onnx"), runtime
        )
        lane_profile = str(inf.get("lane_profile", "yolop"))
        if lane_profile == "twinlitenetplus":
            self.lane = FallbackLaneSegmenter(
                TwinLiteNetPlusSegmenter(
                    ConfigManager.model_path(
                        str(
                            inf.get(
                                "twinlitenetplus_model",
                                "twinlitenetplus_medium.onnx",
                            )
                        )
                    ),
                    runtime,
                ),
                yolop,
            )
        elif lane_profile == "ufldv2_fusion":
            self.lane = FusedLaneSegmenter(
                yolop,
                UFLDv2LaneDetector(
                    ConfigManager.model_path("ufldv2_culane_res18_320x1600.onnx"), runtime
                ),
                int(inf.get("drivable_interval", 4)),
            )
        else:
            self.lane = yolop

    def warmup(self) -> None:
        if self.config.get("enable_objects", True):
            self.objects.load()
        if self.config.get("enable_signs", True):
            self.signs.load()
        if self.config.get("enable_lane", True):
            self.lane.load()

    def status(self) -> dict[str, Any]:
        return {
            "objects": self.objects.status(),
            "signs": self.signs.status(),
            "lane": self.lane.status(),
        }
