from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from .config import ConfigManager


LOGGER = logging.getLogger(__name__)


class UltralyticsDetector:
    def __init__(
        self,
        model_path: Path,
        confidence: float,
        image_size: int,
        device: str = "cpu",
        allowed_classes: list[int] | None = None,
    ) -> None:
        self.model_path = model_path
        self.confidence = confidence
        self.image_size = image_size
        self.device = device
        self.allowed_classes = allowed_classes
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
                        detections.append(
                            {
                                "bbox": [round(float(v), 2) for v in xyxy],
                                "class_id": cid,
                                "label": self.names.get(cid, str(cid)),
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


class PerceptionEngine:
    def __init__(self, config: dict[str, Any]) -> None:
        inf = config["inference"]
        self.config = inf
        self.objects = UltralyticsDetector(
            ConfigManager.model_path("yolo11n.pt"),
            float(inf["object_confidence"]),
            int(inf["image_size"]),
            str(inf.get("device", "cpu")),
            [int(v) for v in inf["road_user_classes"]],
        )
        self.signs = UltralyticsDetector(
            ConfigManager.model_path("yolo11s_vietnam_traffic.pt"),
            float(inf["sign_confidence"]),
            int(inf["image_size"]),
            str(inf.get("device", "cpu")),
        )
        self.lane = YOLOPSegmenter(
            ConfigManager.model_path("yolop_lane_detection_640.onnx"),
            str(inf.get("runtime", "auto")),
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

