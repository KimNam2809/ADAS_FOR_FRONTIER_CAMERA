from __future__ import annotations

import ast
import logging
import json
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import ConfigManager
from .signs import is_speed_limit_label, speed_value


LOGGER = logging.getLogger(__name__)


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
    ) -> None:
        self.model_path = model_path
        self.confidence = confidence
        self.image_size = image_size
        self.runtime = runtime
        self.allowed_classes = allowed_classes
        self.class_thresholds = class_thresholds or {}
        self.session: Any | None = None
        self.provider = "unavailable"
        self.error: str | None = None
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
            import onnxruntime as ort

            available = ort.get_available_providers()
            if self.runtime in {"auto", "directml"} and "DmlExecutionProvider" in available:
                requested = ["DmlExecutionProvider", "CPUExecutionProvider"]
            elif self.runtime in {"auto", "cuda"} and "CUDAExecutionProvider" in available:
                requested = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            else:
                requested = ["CPUExecutionProvider"]
            self.session = ort.InferenceSession(str(self.model_path), providers=requested)
            self.provider = self.session.get_providers()[0]
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
            scale = min(self.image_size / width, self.image_size / height)
            resized_w, resized_h = int(round(width * scale)), int(round(height * scale))
            resized = cv2.resize(frame, (resized_w, resized_h), interpolation=cv2.INTER_LINEAR)
            pad_x = (self.image_size - resized_w) // 2
            pad_y = (self.image_size - resized_h) // 2
            canvas = np.full((self.image_size, self.image_size, 3), 114, dtype=np.uint8)
            canvas[pad_y:pad_y + resized_h, pad_x:pad_x + resized_w] = resized
            rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            tensor = np.transpose(rgb, (2, 0, 1))[None]
            raw = self.session.run(None, {self.session.get_inputs()[0].name: tensor})[0]
            predictions = raw[0]
            if predictions.shape[0] < predictions.shape[1]:
                predictions = predictions.T
            class_scores = predictions[:, 4:]
            class_ids = np.argmax(class_scores, axis=1)
            confidences = class_scores[np.arange(len(class_ids)), class_ids]
            boxes_xywh = predictions[:, :4]
            keep = confidences >= self.confidence
            if self.allowed_classes is not None:
                keep &= np.isin(class_ids, np.asarray(self.allowed_classes))
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
                boxes_xywh = boxes_xywh[threshold_keep]
                confidences = confidences[threshold_keep]
                class_ids = class_ids[threshold_keep]
                kept_class_scores = kept_class_scores[threshold_keep]
            nms_boxes: list[list[float]] = []
            for cx, cy, bw, bh in boxes_xywh:
                nms_boxes.append([float(cx - bw / 2), float(cy - bh / 2), float(bw), float(bh)])
            indices = cv2.dnn.NMSBoxes(nms_boxes, confidences.tolist(), self.confidence, 0.45)
            detections: list[dict[str, Any]] = []
            for index in np.asarray(indices).reshape(-1).tolist() if len(indices) else []:
                x, y, bw, bh = nms_boxes[index]
                x1 = max(0.0, (x - pad_x) / scale)
                y1 = max(0.0, (y - pad_y) / scale)
                x2 = min(float(width), (x + bw - pad_x) / scale)
                y2 = min(float(height), (y + bh - pad_y) / scale)
                class_id = int(class_ids[index])
                top_indices = np.argsort(kept_class_scores[index])[-3:][::-1]
                detections.append(
                    {
                        "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                        "class_id": class_id,
                        "label": self.names.get(class_id, str(class_id)),
                        "confidence": round(float(confidences[index]), 4),
                        "alternatives": [
                            {
                                "class_id": int(alt_id),
                                "label": self.names.get(int(alt_id), str(int(alt_id))),
                                "confidence": round(float(kept_class_scores[index][alt_id]), 4),
                            }
                            for alt_id in top_indices
                        ],
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
            "error": self.error,
        }


class SpeedValueClassifier:
    """Optional second-stage classifier for the digits inside a speed sign."""

    def __init__(self, model_path: Path, confidence: float, device: str = "cpu") -> None:
        self.model_path = model_path
        self.confidence = confidence
        self.device = device
        self.model: Any | None = None
        self.error: str | None = None

    def load(self) -> None:
        if self.model is not None or self.error or not self.model_path.exists():
            return
        try:
            from ultralytics import YOLO

            self.model = YOLO(str(self.model_path))
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.error = str(exc)
            LOGGER.exception("Không thể tải speed-value classifier")

    def classify(self, crops: list[np.ndarray]) -> list[tuple[int | None, float]]:
        self.load()
        if self.model is None or not crops:
            return [(None, 0.0) for _ in crops]
        try:
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
            "loaded": self.model is not None,
            "provider": f"Ultralytics/{self.device}",
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
            import onnxruntime as ort

            available = ort.get_available_providers()
            requested: list[str]
            if self.runtime in {"auto", "directml"} and "DmlExecutionProvider" in available:
                requested = ["DmlExecutionProvider", "CPUExecutionProvider"]
            elif self.runtime in {"auto", "cuda"} and "CUDAExecutionProvider" in available:
                requested = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            else:
                requested = ["CPUExecutionProvider"]
            try:
                self.session = ort.InferenceSession(str(self.model_path), providers=requested)
            except Exception:
                self.session = ort.InferenceSession(
                    str(self.model_path), providers=["CPUExecutionProvider"]
                )
            self.provider = self.session.get_providers()[0]
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
            import onnxruntime as ort

            available = ort.get_available_providers()
            if self.runtime in {"auto", "directml"} and "DmlExecutionProvider" in available:
                providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
            elif self.runtime in {"auto", "cuda"} and "CUDAExecutionProvider" in available:
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            else:
                providers = ["CPUExecutionProvider"]
            try:
                self.session = ort.InferenceSession(str(self.model_path), providers=providers)
            except Exception:
                self.session = ort.InferenceSession(
                    str(self.model_path), providers=["CPUExecutionProvider"]
                )
            self.provider = self.session.get_providers()[0]
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
        self.lane = (
            FusedLaneSegmenter(
                yolop,
                UFLDv2LaneDetector(
                    ConfigManager.model_path("ufldv2_culane_res18_320x1600.onnx"), runtime
                ),
                int(inf.get("drivable_interval", 4)),
            )
            if lane_profile == "ufldv2_fusion"
            else yolop
        )

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
