from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "kaggle/lane_v2_quality_gate/roadwatch_lane_v2_quality_gate.py"
SPEC = importlib.util.spec_from_file_location("lane_v2_quality_gate", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_kernel_requires_gpu_and_target_inputs() -> None:
    metadata = json.loads((SCRIPT.parent / "kernel-metadata.json").read_text(encoding="utf-8"))
    assert metadata["enable_gpu"] == "true"
    assert "lekimnam/roadwatch-target-domain-videos-v1" in metadata["dataset_sources"]
    assert "lekimnam/roadwatch-lane-teacher-models-v1" in metadata["dataset_sources"]


def test_geometry_accepts_ordered_ego_boundaries() -> None:
    ys = list(range(300, 700, 15))
    lanes = [
        {"lane_id": 1, "role": "ego_boundary", "points": [[420, y] for y in ys]},
        {"lane_id": 2, "role": "ego_boundary", "points": [[850, y] for y in ys]},
        {"lane_id": 0, "role": "side_boundary", "points": []},
        {"lane_id": 3, "role": "side_boundary", "points": []},
    ]
    accepted, reasons, metrics = MODULE.validate_geometry(lanes, 1280)
    assert accepted
    assert reasons == []
    assert 0.12 <= metrics["lane_width_ratio"] <= 0.85


def test_geometry_rejects_crossed_or_missing_boundaries() -> None:
    points = [[500, y] for y in range(300, 700, 15)]
    crossed = [
        {"lane_id": 1, "role": "ego_boundary", "points": [[900, y] for _, y in points]},
        {"lane_id": 2, "role": "ego_boundary", "points": [[300, y] for _, y in points]},
    ]
    accepted, reasons, _ = MODULE.validate_geometry(crossed, 1280)
    assert not accepted
    assert "crossed_ego_boundaries" in reasons


def test_decoder_contract_uses_four_lane_instances() -> None:
    outputs = {
        "loc_row": np.zeros((1, 100, 72, 4), dtype=np.float32),
        "loc_col": np.zeros((1, 100, 81, 4), dtype=np.float32),
        "exist_row": np.zeros((1, 2, 72, 4), dtype=np.float32),
        "exist_col": np.zeros((1, 2, 81, 4), dtype=np.float32),
    }
    lanes = MODULE.decode(outputs, 1280, 720)
    assert [lane["lane_id"] for lane in lanes] == [1, 2, 0, 3]
    assert [lane["role"] for lane in lanes] == ["ego_boundary", "ego_boundary", "side_boundary", "side_boundary"]


def test_video_plan_contains_all_required_conditions() -> None:
    assert set(MODULE.VIDEO_PLAN) == {
        "dashcam_vietnam.mp4",
        "dashcam_vietnam_traffic_multi.mp4",
        "dashcam_vietnam_night.mp4",
        "dashcam_vietnam_rainnight.mp4",
    }


def test_ffmpeg_empty_output_is_a_decode_miss(monkeypatch) -> None:
    class EmptyResult:
        stdout = b""

    monkeypatch.setattr(MODULE.subprocess, "run", lambda *args, **kwargs: EmptyResult())
    assert MODULE.read_frame_with_ffmpeg(Path("missing.mp4"), 1.0) is None
