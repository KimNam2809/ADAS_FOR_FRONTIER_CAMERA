import numpy as np

from roadwatch.risk import RiskEngine


CONFIG = {
    "tracking": {"confirmation_hits": 3},
    "risk": {
        "fcw_warning": 0.56,
        "fcw_critical": 0.78,
        "fcw_rearm_hysteresis": 0.08,
        "vulnerable_warning": 0.52,
        "cut_in_warning": 0.60,
        "lane_quality_min": 0.48,
        "ldw_offset_warning": 0.34,
        "ldw_confirmation_frames": 5,
        "speed_sign_confirmation_hits": 3,
        "critical_confidence_min": 0.55,
    },
}


def lane_output() -> dict:
    lane = np.zeros((480, 640), dtype=np.uint8)
    drive = np.zeros((480, 640), dtype=np.uint8)
    for y in range(230, 470):
        progress = (y - 230) / 240
        left = int(285 - 170 * progress)
        right = int(355 + 170 * progress)
        lane[y, max(0, left - 2): left + 3] = 1
        lane[y, right - 2: min(640, right + 3)] = 1
        drive[y, left:right] = 1
    return {"lane_mask": lane, "drivable_mask": drive, "quality": 0.95}


def test_approaching_vehicle_produces_fcw_evidence() -> None:
    engine = RiskEngine(CONFIG)
    tracks = [{
        "track_id": 7,
        "label": "car",
        "class_id": 2,
        "bbox": [235, 190, 405, 455],
        "confidence": 0.92,
        "hits": 6,
        "confirmed": True,
        "age_seconds": 1.2,
        "expansion_rate": 0.4,
        "lateral_velocity": 0.0,
    }]
    candidates, enriched, lane = engine.analyze(
        tracks, [], lane_output(), (480, 640), sign_fresh=False
    )
    assert lane["quality"] > 0.48
    assert enriched[0]["risk_score"] >= CONFIG["risk"]["fcw_warning"]
    assert any(item["event_type"] == "fcw" for item in candidates)
    assert candidates[0]["evidence"]["method"].startswith("image-space")


def test_single_frame_detection_is_not_alerted() -> None:
    engine = RiskEngine(CONFIG)
    tracks = [{
        "track_id": 1,
        "label": "motorcycle",
        "class_id": 3,
        "bbox": [250, 200, 390, 460],
        "confidence": 0.95,
        "hits": 1,
        "confirmed": False,
        "age_seconds": 0.0,
        "expansion_rate": 0.8,
        "lateral_velocity": 0.0,
    }]
    candidates, _, _ = engine.analyze(tracks, [], lane_output(), (480, 640), False)
    assert candidates == []


def test_near_field_vehicle_is_not_blocked_by_bad_lane_mask() -> None:
    engine = RiskEngine(CONFIG)
    bad_lane = {
        "lane_mask": np.zeros((480, 640), dtype=np.uint8),
        "drivable_mask": np.zeros((480, 640), dtype=np.uint8),
        "quality": 0.0,
    }
    track = {
        "track_id": 12,
        "label": "car",
        "class_id": 2,
        "bbox": [350, 180, 620, 470],
        "confidence": 0.9,
        "hits": 6,
        "confirmed": True,
        "age_seconds": 1.0,
        "expansion_rate": 0.12,
        "lateral_velocity": -0.04,
    }
    candidates, enriched, lane = engine.analyze(
        [track], [], bad_lane, (480, 640), sign_fresh=False
    )
    assert lane["quality"] == 0
    assert enriched[0]["near_field_threat"] is True
    assert any(item["event_type"] == "fcw" for item in candidates)


def test_fcw_requires_risk_to_rearm_before_repeating() -> None:
    engine = RiskEngine(CONFIG)
    high = {
        "track_id": 9,
        "label": "car",
        "class_id": 2,
        "bbox": [235, 190, 405, 455],
        "confidence": 0.92,
        "hits": 6,
        "confirmed": True,
        "age_seconds": 1.2,
        "expansion_rate": 0.4,
        "lateral_velocity": 0.0,
    }
    first, _, _ = engine.analyze([high], [], lane_output(), (480, 640), False)
    repeated, _, _ = engine.analyze([high], [], lane_output(), (480, 640), False)
    assert any(item["event_type"] == "fcw" for item in first)
    assert not any(item["event_type"] == "fcw" for item in repeated)

    low = {**high, "bbox": [300, 80, 340, 130], "expansion_rate": 0.0}
    engine.analyze([low], [], lane_output(), (480, 640), False)
    rearmed, _, _ = engine.analyze([high], [], lane_output(), (480, 640), False)
    assert any(item["event_type"] == "fcw" for item in rearmed)


def test_candidate_rider_class_is_treated_as_vulnerable_road_user() -> None:
    engine = RiskEngine(CONFIG)
    rider = {
        "track_id": 21,
        "label": "rider",
        "class_id": 1,
        "bbox": [255, 190, 390, 460],
        "confidence": 0.9,
        "hits": 6,
        "confirmed": True,
        "age_seconds": 1.0,
        "expansion_rate": 0.25,
        "lateral_velocity": 0.0,
    }
    candidates, _, _ = engine.analyze(
        [rider], [], lane_output(), (480, 640), sign_fresh=False
    )
    types = {candidate["event_type"] for candidate in candidates}
    assert "fcw" in types
    assert "vulnerable_road_user" in types
    assert any("Người đi xe hai bánh" in candidate["message"] for candidate in candidates)
