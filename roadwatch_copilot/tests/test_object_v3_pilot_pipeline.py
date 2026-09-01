from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "kaggle/train_object_v3_pilot/roadwatch_train_object_v3_pilot.py"
METADATA = SCRIPT.parent / "kernel-metadata.json"


def load_pipeline():
    spec = importlib.util.spec_from_file_location("roadwatch_train_object_v3_pilot", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pilot_kernel_contract() -> None:
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    assert metadata["id"] == "lekimnam/roadwatch-object-detector-v3-pilot"
    assert metadata["enable_gpu"] == "true"
    assert metadata["code_file"] == "roadwatch_train_object_v3_pilot.py"
    assert "a7madmostafa/bdd100k-yolo" in metadata["dataset_sources"]
    assert "orvile/dawn-detection-in-adverse-weather-nature" in metadata["dataset_sources"]
    assert "lekimnam/roadwatch-target-domain-videos-v1" in metadata["dataset_sources"]


def test_pilot_defaults_to_one_epoch_and_preserves_seven_class_taxonomy() -> None:
    pipeline = load_pipeline()
    assert pipeline.RUN_MODE == "pilot_1_epoch"
    assert pipeline.EPOCHS == 1
    assert pipeline.CANONICAL == [
        "person",
        "rider",
        "bicycle",
        "motorcycle",
        "car",
        "bus",
        "truck",
    ]
    assert pipeline.OUTPUT.name == "roadwatch_object_v3_pilot"
    assert pipeline.RUN_NAME == "roadwatch_objects_v3_pilot_1e"


def test_pilot_never_allows_automatic_promotion() -> None:
    readme = (SCRIPT.parent / "README.md").read_text(encoding="utf-8")
    assert "never auto-promotes" in readme
    assert "target-domain labels remain pseudo labels" in readme.lower()
