from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_lane_review_queue_v2.py"
SPEC = importlib.util.spec_from_file_location("build_lane_review_queue_v2", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_payload() -> dict:
    return {
        "records": [
            {
                "id": "rain-1",
                "source": "rain.mp4",
                "split": "test",
                "condition": "rain_night",
                "timestamp_s": 1.0,
                "frame_index": 30,
                "accepted": False,
                "label_status": "rejected_by_geometry",
                "rejection_reasons": ["missing_ego_boundary"],
                "lane_instances": [],
                "geometry": {},
                "review_image": "rain-1.jpg",
            },
            {
                "id": "day-1",
                "source": "day.mp4",
                "split": "train",
                "condition": "day",
                "timestamp_s": 2.0,
                "frame_index": 60,
                "accepted": True,
                "label_status": "candidate_unverified",
                "rejection_reasons": [],
                "lane_instances": [{"lane_id": 1}],
                "geometry": {"lane_width_ratio": 0.4},
                "review_image": "day-1.jpg",
            },
        ]
    }


def test_queue_keeps_model_proposal_separate_from_ground_truth() -> None:
    queue = MODULE.build_queue(source_payload(), "artifact/root")
    assert queue["records"][0]["conditions"] == ["rain_night"]
    assert queue["records"][0]["review_status"] == "pending"
    assert queue["records"][0]["ground_truth_lane_count"] is None
    assert queue["records"][0]["model_proposal"]["accepted"] is False


def test_queue_prioritizes_adverse_conditions_and_validates_split() -> None:
    queue = MODULE.build_queue(source_payload(), "artifact/root")
    validation = MODULE.validate_queue(queue)
    assert validation["status"] == "pass"
    assert queue["records"][0]["source"] == "rain.mp4"
    assert validation["split_source_overlap"] is False


def test_validation_rejects_prefilled_ground_truth() -> None:
    queue = MODULE.build_queue(source_payload(), "artifact/root")
    queue["records"][0]["ego_left_boundary"] = [[1, 2], [3, 4]]
    validation = MODULE.validate_queue(queue)
    assert validation["status"] == "fail"
    assert any("polyline_prefilled" in item for item in validation["invalid_fields"])
