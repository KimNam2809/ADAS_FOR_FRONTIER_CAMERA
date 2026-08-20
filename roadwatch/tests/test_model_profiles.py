from pathlib import Path

from roadwatch.config import ConfigManager
from roadwatch.perception import PerceptionEngine


def test_baseline_profile_uses_coco_class_ids(tmp_path: Path) -> None:
    config = ConfigManager(runtime_path=tmp_path / "missing.json").snapshot()
    engine = PerceptionEngine(config)
    assert engine.objects.allowed_classes == [0, 1, 2, 3, 5, 7]
    assert engine.objects.model_path.name in {"yolo11n.pt", "yolo11n.onnx"}


def test_candidate_profile_uses_canonical_class_ids(tmp_path: Path) -> None:
    manager = ConfigManager(runtime_path=tmp_path / "missing.json")
    manager.update(
        {
            "inference": {
                "object_profile": "roadwatch_objects_v1",
                "prefer_onnx_detectors": False,
            }
        },
        persist=False,
    )
    engine = PerceptionEngine(manager.snapshot())
    assert engine.objects.allowed_classes == list(range(7))
    assert engine.objects.model_path.name == "roadwatch_objects_v1.pt"


def test_unknown_profile_is_rejected(tmp_path: Path) -> None:
    manager = ConfigManager(runtime_path=tmp_path / "missing.json")
    try:
        manager.update({"inference": {"object_profile": "unknown"}}, persist=False)
    except ValueError as error:
        assert "không tồn tại" in str(error)
    else:
        raise AssertionError("Unknown model profile must be rejected")


def test_phase2_1_candidate_profile_uses_canonical_taxonomy(tmp_path: Path) -> None:
    manager = ConfigManager(runtime_path=tmp_path / "missing.json")
    manager.update(
        {
            "inference": {
                "object_profile": "roadwatch_objects_v1_1",
                "prefer_onnx_detectors": False,
            }
        },
        persist=False,
    )
    engine = PerceptionEngine(manager.snapshot())
    assert engine.objects.allowed_classes == list(range(7))
    assert engine.objects.model_path.name == "roadwatch_objects_v1_1.pt"
    assert engine.objects.class_thresholds["car"] == 0.55
    assert engine.objects.class_thresholds["motorcycle"] == 0.42
