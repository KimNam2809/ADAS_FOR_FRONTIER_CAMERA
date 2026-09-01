from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "kaggle/train_object_v2/roadwatch_train_object_v2.py"


def load_pipeline():
    spec = importlib.util.spec_from_file_location("roadwatch_train_object_v2", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_background_sampling_is_two_fps_and_includes_zero() -> None:
    pipeline = load_pipeline()
    assert pipeline.BACKGROUND_SAMPLING_FPS == 2
    assert pipeline.background_sample_seconds(2.0) == {0.0, 0.5, 1.0, 1.5, 2.0}


def test_background_sampling_rejects_negative_duration() -> None:
    pipeline = load_pipeline()
    try:
        pipeline.background_sample_seconds(-0.1)
    except ValueError as exc:
        assert "negative" in str(exc)
    else:
        raise AssertionError("negative duration must fail closed")
