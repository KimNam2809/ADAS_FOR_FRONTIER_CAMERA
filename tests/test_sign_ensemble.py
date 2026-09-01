import numpy as np

from roadwatch.perception import TrafficSignEnsemble, _parse_model_names


def test_onnx_names_metadata_supports_ultralytics_python_repr() -> None:
    assert _parse_model_names("{0: 'No Entry', 2: 'speed_limit'}") == {
        0: "No Entry",
        2: "speed_limit",
    }


def test_onnx_names_metadata_rejects_malformed_value() -> None:
    assert _parse_model_names("not-a-name-map") == {}


class FakeDetector:
    def load(self) -> None:
        pass

    def infer(self, frame):
        return [
            {
                "bbox": [20, 20, 60, 60],
                "class_id": 40,
                "label": "40",
                "confidence": 0.9,
            }
        ], 4.0

    def status(self):
        return {"model": "fake", "available": True, "loaded": True}


class FakeClassifier:
    def load(self) -> None:
        pass

    def classify(self, crops):
        assert len(crops) == 1
        return [(60, 0.95)]

    def status(self):
        return {"model": "fake-cls", "available": True, "loaded": True}


def test_speed_crop_classifier_corrects_detector_semantics() -> None:
    ensemble = TrafficSignEnsemble(FakeDetector(), FakeClassifier())
    detections, latency = ensemble.infer(np.zeros((100, 100, 3), dtype=np.uint8))
    assert latency >= 4.0
    assert detections[0]["label"] == "60"
    assert detections[0]["class_id"] == 10060
    assert detections[0]["detector_label"] == "40"
    assert detections[0]["speed_value_source"] == "crop_classifier"


class GenericSpeedDetector(FakeDetector):
    def infer(self, frame):
        detections, latency = super().infer(frame)
        detections[0]["label"] = "speed_limit"
        detections[0]["class_id"] = 2
        return detections, latency


def test_generic_speed_detector_is_resolved_by_crop_classifier() -> None:
    ensemble = TrafficSignEnsemble(GenericSpeedDetector(), FakeClassifier())
    detections, _ = ensemble.infer(np.zeros((100, 100, 3), dtype=np.uint8))
    assert detections[0]["label"] == "60"
    assert detections[0]["detector_label"] == "speed_limit"
    assert detections[0]["speed_value_source"] == "crop_classifier"


class UnknownSpeedClassifier(FakeClassifier):
    def classify(self, crops):
        assert len(crops) == 1
        return [(None, 0.99)]


def test_unknown_speed_value_never_becomes_numeric_claim() -> None:
    ensemble = TrafficSignEnsemble(GenericSpeedDetector(), UnknownSpeedClassifier())
    detections, _ = ensemble.infer(np.zeros((100, 100, 3), dtype=np.uint8))
    assert detections[0]["label"] == "speed_limit"
    assert detections[0]["class_id"] == 2
    assert detections[0]["speed_classifier_confidence"] == 0.99
    assert "speed_value_source" not in detections[0]
