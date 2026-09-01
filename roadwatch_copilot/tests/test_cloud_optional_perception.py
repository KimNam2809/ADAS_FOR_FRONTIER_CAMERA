from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from roadwatch.optional_perception import OptionalPerceptionWorker
from roadwatch.perception import OnnxYoloDetector, SpeedValueClassifier


class _Input:
    name = "images"
    shape = [1, 3, 640, 640]


class _Metadata:
    custom_metadata_map = {"names": "{0: 'car'}"}


class _DetectorSession:
    def __init__(self) -> None:
        self.feed_shape: tuple[int, ...] | None = None

    def get_inputs(self):
        return [_Input()]

    def get_modelmeta(self):
        return _Metadata()

    def run(self, _outputs, feed):
        self.feed_shape = next(iter(feed.values())).shape
        return [np.zeros((1, 5, 1), dtype=np.float32)]


class _EndToEndDetectorSession:
    def get_inputs(self):
        return [_Input()]

    def get_modelmeta(self):
        return _Metadata()

    def run(self, _outputs, _feed):
        output = np.zeros((1, 300, 6), dtype=np.float32)
        output[0, 0] = [100.0, 200.0, 220.0, 360.0, 0.91, 0.0]
        return [output]


def test_fixed_shape_onnx_detector_uses_model_input_not_cloud_object_size(monkeypatch) -> None:
    session = _DetectorSession()
    monkeypatch.setattr(
        "roadwatch.perception._create_onnx_session",
        lambda _path, _runtime, _optional=False: (session, "CPUExecutionProvider"),
    )
    detector = OnnxYoloDetector(Path("fixed-sign.onnx"), 0.4, 320, "cpu")
    detector.load()
    detections, _ = detector.infer(np.zeros((360, 640, 3), dtype=np.uint8))
    assert detections == []
    assert session.feed_shape == (1, 3, 640, 640)
    assert detector.status()["input_size"] == "640x640"


def test_end_to_end_onnx_detector_decodes_yolo26_output(monkeypatch) -> None:
    session = _EndToEndDetectorSession()
    monkeypatch.setattr(
        "roadwatch.perception._create_onnx_session",
        lambda _path, _runtime, _optional=False: (session, "CPUExecutionProvider"),
    )
    detector = OnnxYoloDetector(Path("yolo26n.onnx"), 0.4, 640, "cpu", [0])
    detections, _ = detector.infer(np.zeros((360, 640, 3), dtype=np.uint8))
    assert len(detections) == 1
    assert detections[0]["class_id"] == 0
    assert detections[0]["label"] == "car"
    assert detections[0]["confidence"] == 0.91


class _ClassifierInput:
    name = "images"


class _ClassifierSession:
    def get_inputs(self):
        return [_ClassifierInput()]

    def run(self, _outputs, feed):
        assert next(iter(feed.values())).shape == (1, 3, 160, 160)
        probabilities = np.zeros((1, 2), dtype=np.float32)
        probabilities[0, 0] = 0.98
        return [probabilities]


def test_speed_classifier_onnx_returns_promoted_speed_value() -> None:
    classifier = SpeedValueClassifier(Path("speed.onnx"), 0.95, "cpu")
    classifier.session = _ClassifierSession()
    classifier.names = {0: "60", 1: "unknown"}
    value, confidence = classifier.classify([np.zeros((24, 24, 3), dtype=np.uint8)])[0]
    assert value == 60
    assert round(confidence, 2) == 0.98


class _Metrics:
    def __init__(self) -> None:
        self.names: list[str] = []

    def observe(self, name: str, _latency: float) -> None:
        self.names.append(name)


class _Head:
    def __init__(self, result) -> None:
        self.result = result

    def infer(self, _frame):
        return self.result, 5.0


def test_optional_worker_publishes_latest_session_scoped_cache() -> None:
    metrics = _Metrics()
    worker = OptionalPerceptionWorker(
        _Head([{"label": "60"}]),
        _Head({"quality": 0.8}),
        metrics,
        sign_interval=2,
        sign_candidate_interval=1,
        lane_interval=3,
        max_staleness_seconds=1.5,
    )
    worker.reset()
    worker.start()
    try:
        worker.submit(np.zeros((8, 8, 3), dtype=np.uint8), 1, 1.0)
        deadline = time.time() + 1.0
        snapshot = worker.snapshot(1.0)
        while snapshot["sign_sequence"] == 0 and time.time() < deadline:
            time.sleep(0.01)
            snapshot = worker.snapshot(1.0)
        assert snapshot["signs"] == [{"label": "60"}]
        assert snapshot["lane"] == {"quality": 0.8}
        assert set(metrics.names) == {"traffic_sign", "lane_detection"}
        worker.reset()
        cleared = worker.snapshot(1.1)
        assert cleared["signs"] == []
        assert cleared["lane"] is None
    finally:
        worker.close()
