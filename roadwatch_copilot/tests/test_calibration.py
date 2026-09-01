from roadwatch.calibration import validate_calibration


def valid_artifact() -> dict:
    return {
        "schema_version": 1,
        "calibrated": True,
        "camera_id": "front-camera-test",
        "image_size": [1920, 1080],
        "fx": 1000.0,
        "fy": 1001.0,
        "cx": 960.0,
        "cy": 540.0,
        "distortion_coefficients": [0, 0, 0, 0, 0],
        "valid_image_count": 12,
        "source_image_sha256": ["A" * 64] * 12,
        "rms_reprojection_error": 0.45,
        "quality_gate": {"metric_ttc_alerting_allowed": False},
    }


def test_valid_calibration_artifact_passes() -> None:
    assert validate_calibration(valid_artifact()) == []


def test_calibration_cannot_self_authorize_metric_alerting() -> None:
    artifact = valid_artifact()
    artifact["quality_gate"]["metric_ttc_alerting_allowed"] = True
    assert any("must not enable" in error for error in validate_calibration(artifact))


def test_calibration_requires_reproducible_source_hashes() -> None:
    artifact = valid_artifact()
    artifact["source_image_sha256"] = []
    assert any("one SHA-256" in error for error in validate_calibration(artifact))
