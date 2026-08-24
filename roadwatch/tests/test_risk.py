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
        "trajectory_horizon_seconds": 1.5,
        "hazard_confirmation_frames": 1,
        "critical_confirmation_frames": 1,
        "trajectory_confirmation_frames": 1,
        "critical_proximity_min": 0.65,
        "critical_approach_min": 0.18,
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
        "relative_closing_rate_per_s": 0.30,
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
        "relative_closing_rate_per_s": 0.30,
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
        "relative_closing_rate_per_s": 0.30,
    }
    first, _, _ = engine.analyze([high], [], lane_output(), (480, 640), False)
    repeated, _, _ = engine.analyze([high], [], lane_output(), (480, 640), False)
    assert any(item["event_type"] == "fcw" for item in first)
    assert not any(item["event_type"] == "fcw" for item in repeated)

    low = {
        **high,
        "bbox": [300, 80, 340, 130],
        "expansion_rate": 0.0,
        "relative_closing_rate_per_s": 0.0,
    }
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
        "relative_closing_rate_per_s": 0.30,
    }
    candidates, _, _ = engine.analyze(
        [rider], [], lane_output(), (480, 640), sign_fresh=False
    )
    types = {candidate["event_type"] for candidate in candidates}
    assert "fcw" in types
    assert "vulnerable_road_user" in types
    assert any("Người đi xe hai bánh" in candidate["message"] for candidate in candidates)


def test_emergency_bbox_override_prevents_silent_fcw_after_closing_rate_drops() -> None:
    engine = RiskEngine(CONFIG)
    stopped_close_lead = {
        "track_id": 30,
        "label": "car",
        "class_id": 2,
        "bbox": [170, 100, 470, 479],
        "confidence": 0.92,
        "hits": 8,
        "confirmed": True,
        "age_seconds": 1.4,
        "expansion_rate": 0.0,
        "lateral_velocity": 0.0,
        "relative_closing_rate_per_s": 0.0,
        "motion_observations": 8,
    }
    candidates, enriched, _ = engine.analyze(
        [stopped_close_lead], [], lane_output(), (480, 640), sign_fresh=False
    )
    fcw = next(item for item in candidates if item["event_type"] == "fcw")
    assert fcw["severity"] == "critical"
    assert fcw["message"] == "Cảnh báo va chạm phía trước!"
    assert fcw["evidence"]["trigger_path"] == "image_space_emergency_override"
    assert enriched[0]["emergency_near_field"] is True


def test_static_roadside_object_cannot_trigger_cross_traffic_from_jitter_only() -> None:
    engine = RiskEngine(CONFIG)
    bad_lane = {
        "lane_mask": np.zeros((480, 640), dtype=np.uint8),
        "drivable_mask": np.zeros((480, 640), dtype=np.uint8),
        "quality": 0.0,
    }
    parked = {
        "track_id": 31,
        "label": "car",
        "class_id": 2,
        "bbox": [470, 220, 610, 420],
        "confidence": 0.9,
        "hits": 8,
        "confirmed": True,
        "age_seconds": 1.2,
        "expansion_rate": 0.0,
        "lateral_velocity": -0.04,
        "origin_x_norm": 0.84,
        "displacement_x_norm": -0.004,
        "displacement_y_norm": 0.001,
        "motion_observations": 8,
    }
    candidates, _, _ = engine.analyze(
        [parked], [], bad_lane, (480, 640), sign_fresh=False
    )
    assert not any(item["event_type"] == "cross_traffic" for item in candidates)


def test_cross_traffic_direction_must_agree_with_origin_side() -> None:
    engine = RiskEngine(CONFIG)
    bad_lane = {
        "lane_mask": np.zeros((480, 640), dtype=np.uint8),
        "drivable_mask": np.zeros((480, 640), dtype=np.uint8),
        "quality": 0.0,
    }
    moving_away_from_center = {
        "track_id": 34,
        "label": "truck",
        "class_id": 7,
        "bbox": [430, 180, 570, 390],
        "confidence": 0.9,
        "hits": 8,
        "confirmed": True,
        "age_seconds": 1.2,
        "expansion_rate": 0.0,
        "lateral_velocity": 0.08,
        "relative_closing_rate_per_s": 0.10,
        "origin_x_norm": 0.72,
        "displacement_x_norm": 0.08,
        "displacement_y_norm": 0.01,
        "motion_observations": 8,
    }
    candidates, _, _ = engine.analyze(
        [moving_away_from_center], [], bad_lane, (480, 640), sign_fresh=False
    )
    assert not any(item["event_type"] == "cross_traffic" for item in candidates)


def test_low_confidence_short_vehicle_track_is_not_cross_traffic() -> None:
    engine = RiskEngine(CONFIG)
    bad_lane = {
        "lane_mask": np.zeros((480, 640), dtype=np.uint8),
        "drivable_mask": np.zeros((480, 640), dtype=np.uint8),
        "quality": 0.0,
    }
    noisy_truck = {
        "track_id": 36,
        "label": "truck",
        "class_id": 7,
        "bbox": [430, 180, 570, 390],
        "confidence": 0.46,
        "hits": 5,
        "confirmed": True,
        "age_seconds": 0.8,
        "expansion_rate": 0.0,
        "lateral_velocity": -0.10,
        "relative_closing_rate_per_s": 0.0,
        "origin_x_norm": 0.82,
        "displacement_x_norm": -0.12,
        "displacement_y_norm": 0.04,
        "motion_observations": 5,
    }
    candidates, _, _ = engine.analyze(
        [noisy_truck], [], bad_lane, (480, 640), sign_fresh=False
    )
    assert not any(item["event_type"] == "cross_traffic" for item in candidates)


def test_right_lane_merge_is_cut_in_with_right_origin_not_cross_traffic() -> None:
    engine = RiskEngine(CONFIG)
    bad_lane = {
        "lane_mask": np.zeros((480, 640), dtype=np.uint8),
        "drivable_mask": np.zeros((480, 640), dtype=np.uint8),
        "quality": 0.0,
    }
    merging = {
        "track_id": 32,
        "label": "car",
        "class_id": 2,
        "bbox": [420, 190, 560, 430],
        "confidence": 0.93,
        "hits": 8,
        "confirmed": True,
        "age_seconds": 1.2,
        "expansion_rate": 0.08,
        "lateral_velocity": -0.15,
        "origin_x_norm": 0.86,
        "displacement_x_norm": -0.12,
        "displacement_y_norm": 0.18,
        "motion_observations": 8,
    }
    candidates, _, _ = engine.analyze(
        [merging], [], bad_lane, (480, 640), sign_fresh=False
    )
    cut_in = next(item for item in candidates if item["event_type"] == "cut_in")
    assert "bên phải" in cut_in["message"]
    assert cut_in["evidence"]["origin_side"] == "right"
    assert not any(item["event_type"] == "cross_traffic" for item in candidates)


def test_imminent_side_entry_can_override_failed_lane_corridor_for_fcw() -> None:
    engine = RiskEngine(CONFIG)
    bad_lane = {
        "lane_mask": np.zeros((480, 640), dtype=np.uint8),
        "drivable_mask": np.zeros((480, 640), dtype=np.uint8),
        "quality": 0.0,
    }
    close_right = {
        "track_id": 33,
        "label": "car",
        "class_id": 2,
        "bbox": [360, 80, 638, 479],
        "confidence": 0.94,
        "hits": 9,
        "confirmed": True,
        "age_seconds": 1.5,
        "expansion_rate": 0.45,
        "lateral_velocity": -0.04,
        "relative_closing_rate_per_s": 0.0,
        "origin_x_norm": 0.86,
        "displacement_x_norm": -0.09,
        "displacement_y_norm": 0.12,
        "motion_observations": 9,
    }
    candidates, enriched, _ = engine.analyze(
        [close_right], [], bad_lane, (480, 640), sign_fresh=False
    )
    assert enriched[0]["path_conflict"] is False
    assert enriched[0]["near_field_imminent"] is True
    assert enriched[0]["emergency_near_field"] is True
    assert any(
        item["event_type"] == "fcw" and item["severity"] == "critical"
        for item in candidates
    )


def test_cross_traffic_is_suppressed_after_critical_fcw_for_same_track() -> None:
    engine = RiskEngine(CONFIG)
    bad_lane = {
        "lane_mask": np.zeros((480, 640), dtype=np.uint8),
        "drivable_mask": np.zeros((480, 640), dtype=np.uint8),
        "quality": 0.0,
    }
    critical = {
        "track_id": 35,
        "label": "car",
        "class_id": 2,
        "bbox": [170, 100, 470, 479],
        "confidence": 0.94,
        "hits": 9,
        "confirmed": True,
        "age_seconds": 1.5,
        "expansion_rate": 0.4,
        "lateral_velocity": 0.0,
        "relative_closing_rate_per_s": 0.5,
        "origin_x_norm": 0.7,
        "displacement_x_norm": -0.08,
        "displacement_y_norm": 0.12,
        "motion_observations": 9,
    }
    first, _, _ = engine.analyze(
        [critical], [], bad_lane, (480, 640), sign_fresh=False
    )
    assert any(item["event_type"] == "fcw" for item in first)
    receding_laterally = {
        **critical,
        "bbox": [410, 190, 550, 390],
        "expansion_rate": 0.0,
        "lateral_velocity": -0.08,
        "relative_closing_rate_per_s": 0.0,
        "displacement_x_norm": -0.10,
        "displacement_y_norm": 0.01,
    }
    second, _, _ = engine.analyze(
        [receding_laterally], [], bad_lane, (480, 640), sign_fresh=False
    )
    assert not any(item["event_type"] == "cross_traffic" for item in second)
