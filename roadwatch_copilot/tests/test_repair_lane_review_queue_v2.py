from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/repair_lane_review_queue_v2.py"
SPEC = importlib.util.spec_from_file_location("repair_lane_review_queue_v2", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def record(**overrides):
    value = {
        "id": "r1",
        "source": "night.mp4",
        "split": "val",
        "review_status": "verified",
        "ground_truth_lane_count": 1,
        "ego_left_boundary": [[300, 900], [500, 1080]],
        "ego_right_boundary": [[1500, 900], [1600, 1080]],
        "review_notes": "",
    }
    value.update(overrides)
    return value


def test_unique_y_scale_is_repaired() -> None:
    value = record(
        ego_left_boundary=[[300, 2700], [500, 3240]],
        ego_right_boundary=[[1500, 2700], [1600, 3240]],
    )
    repaired = MODULE.repair_record(value)
    assert repaired["review_status"] == "verified"
    assert repaired["ego_left_boundary"] == [[300, 900], [500, 1080]]
    assert repaired["repair_status"] == "auto_repaired"


def test_zero_lane_with_polyline_is_quarantined() -> None:
    repaired = MODULE.repair_record(record(ground_truth_lane_count=0))
    assert repaired["review_status"] == "needs_recheck"
    assert "zero_lane_count_with_polyline" in repaired["repair_notes"]


def test_mixed_scale_is_not_guessed() -> None:
    value = record(ego_left_boundary=[[300, 900], [500, 3240]])
    repaired = MODULE.repair_record(value)
    assert repaired["review_status"] == "needs_recheck"
    assert "ambiguous_coordinate_scale" in repaired["repair_notes"]


def test_post_validation_rejects_unrepaired_verified_point() -> None:
    result = MODULE.validate_post({"records": [record(ego_left_boundary=[[1, 2000]])]})
    assert result["status"] == "fail"
    assert "out_of_frame_point" in result["issues"][0]
