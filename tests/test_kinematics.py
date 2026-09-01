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
    estimator.enrich([_track(60)], 0.0)
    estimator.enrich([_track(75)], 0.5)
    result = estimator.enrich([_track(100)], 1.0)
    assert result[0]["metric_ttc_available"] is False
    assert result[0]["kinematics_space"] == "image_space"
    assert result[0]["relative_closing_rate_per_s"] > 0
    assert result[0]["relative_ttc_proxy_seconds"] is not None
    assert result[0]["relative_kinematics_role"] == "advisory_image_space_only"
    assert estimator.status()["enabled"] is False


def test_calibrated_estimator_reports_closing_telemetry_only(tmp_path) -> None:
    calibration = tmp_path / "camera.json"
    calibration.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "calibrated": True,
                "camera_id": "test-front-camera",
                "image_size": [1920, 1080],
                "fx": 1000.0,
                "fy": 1000.0,
                "cx": 960.0,
                "cy": 540.0,
                "distortion_coefficients": [0, 0, 0, 0, 0],
                "valid_image_count": 12,
                "source_image_sha256": ["A" * 64] * 12,
                "rms_reprojection_error": 0.4,
                "quality_gate": {"metric_ttc_alerting_allowed": False},
            }
        ),
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
    assert result["kinematics_space"] == "image_space"
