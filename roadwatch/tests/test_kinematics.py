import json

from roadwatch.kinematics import MonocularKinematics


def _track(pixel_height: float) -> dict:
    return {
        "track_id": 1,
        "label": "car",
        "bbox": [100, 300 - pixel_height, 250, 300],
    }


def test_metric_ttc_is_disabled_without_calibration(tmp_path) -> None:
    estimator = MonocularKinematics(tmp_path / "missing.json", enabled=True)
    result = estimator.enrich([_track(100)], 0.0)
    assert result[0]["metric_ttc_available"] is False
    assert estimator.status()["enabled"] is False


def test_calibrated_estimator_reports_closing_telemetry_only(tmp_path) -> None:
    calibration = tmp_path / "camera.json"
    calibration.write_text(
        json.dumps({"calibrated": True, "fy": 1000.0, "rms_reprojection_error": 0.4}),
        encoding="utf-8",
    )
    estimator = MonocularKinematics(calibration, enabled=True)
    estimator.enrich([_track(75)], 0.0)
    estimator.enrich([_track(100)], 0.5)
    result = estimator.enrich([_track(150)], 1.0)[0]
    assert result["metric_ttc_available"] is True
    assert result["distance_m"] == 10.0
    assert result["closing_speed_mps"] > 0
    assert result["metric_ttc_role"] == "telemetry_only"
