import copy
import json
from pathlib import Path

import pytest

from roadwatch.config import ConfigManager
from roadwatch.release import RELEASE_MANIFEST_PATH, verify_release


def _defaults() -> dict:
    missing_runtime = Path(__file__).with_name("__missing_runtime__.json")
    return ConfigManager(runtime_path=missing_runtime).snapshot()


def test_tracked_release_contract_matches_defaults() -> None:
    required = [
        "yolo11n.onnx",
        "roadwatch_detector_v2.onnx",
        "roadwatch_speed_digits_v2.onnx",
        "yolop_lane_detection_640.onnx",
    ]
    missing = [name for name in required if not (Path(__file__).parents[1] / "models" / name).is_file()]
    if missing:
        pytest.skip("External model assets are not present; run setup.ps1 first: " + ", ".join(missing))
    report = verify_release(_defaults(), verify_hashes=False)
    assert report["status"] == "pass"
    assert report["checks_failed"] == 0


def test_stale_runtime_sign_model_is_rejected() -> None:
    config = copy.deepcopy(_defaults())
    config["inference"]["sign_model"] = "yolo11s_vietnam_traffic.pt"
    report = verify_release(config, verify_hashes=False)
    assert report["status"] == "fail"
    assert any(
        item["name"] == "runtime.sign_model" and item["status"] == "fail"
        for item in report["checks"]
    )


def test_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    manifest = json.loads(RELEASE_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["artifacts"] = [
        {"component": "fixture", "file": "fixture.bin", "sha256": "00" * 32}
    ]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    (tmp_path / "fixture.bin").write_bytes(b"roadwatch")

    report = verify_release(
        _defaults(), manifest_path=manifest_path, model_root=tmp_path, verify_hashes=True
    )
    assert report["status"] == "fail"
    assert any(item["name"].endswith(".sha256") for item in report["checks"])
