from __future__ import annotations

from roadwatch.config import ConfigManager


def test_cloud_profile_uses_onnx_and_skips_pytorch_speed_warmup(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_CLOUD_MODE", "web_demo")
    config = ConfigManager().snapshot()
    assert config["inference"]["prefer_onnx_detectors"] is True
    assert config["inference"]["runtime"] == "cpu"
    assert config["inference"]["speed_classifier_model"].startswith("__cloud_")
    assert config["app"]["max_processed_fps"] <= 6.0
