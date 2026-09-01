from __future__ import annotations

from roadwatch.config import ConfigManager


def test_cloud_profile_uses_onnx_and_skips_pytorch_speed_warmup(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_CLOUD_MODE", "web_demo")
    config = ConfigManager().snapshot()
    assert config["inference"]["prefer_onnx_detectors"] is True
    assert config["inference"]["runtime"] == "cpu"
    assert config["inference"]["speed_classifier_model"].startswith("__cloud_")
    assert config["app"]["max_processed_fps"] <= 6.0


def test_cloud_fast_profile_disables_cpu_heavy_optional_heads(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_CLOUD_MODE", "web_demo")
    monkeypatch.setenv("ROADWATCH_CLOUD_FAST", "1")
    monkeypatch.setenv("ROADWATCH_CLOUD_IMAGE_SIZE", "320")
    config = ConfigManager().snapshot()
    assert config["inference"]["enable_lane"] is False
    assert config["inference"]["enable_signs"] is False
    assert config["inference"]["object_onnx_model"] == "yolo11n_320.onnx"
    assert config["inference"]["image_size"] == 320
    assert config["app"]["max_processed_fps"] <= 4.0


def test_cloud_full_profile_uses_promoted_optional_heads_asynchronously(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_CLOUD_MODE", "web_demo")
    monkeypatch.setenv("ROADWATCH_CLOUD_FAST", "0")
    monkeypatch.setenv("ROADWATCH_CLOUD_FULL", "1")
    monkeypatch.setenv("ROADWATCH_CLOUD_IMAGE_SIZE", "320")
    config = ConfigManager().snapshot()
    inference = config["inference"]
    assert inference["enable_lane"] is True
    assert inference["enable_signs"] is True
    assert inference["async_optional_perception"] is True
    assert inference["object_onnx_model"] == "yolo11n_320.onnx"
    assert inference["sign_onnx_model"] == "roadwatch_detector_v2_416.onnx"
    assert inference["speed_classifier_model"] == "roadwatch_speed_digits_v2.onnx"
    assert inference["lane_profile"] == "yolop"
    assert inference["sign_interval"] == 1
    assert inference["lane_interval"] == 4
    assert config["app"]["max_processed_fps"] <= 4.0
