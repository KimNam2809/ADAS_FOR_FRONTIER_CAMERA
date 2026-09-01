from __future__ import annotations

import numpy as np

from roadwatch.config import ConfigManager
from roadwatch.metrics import MetricsCollector
from roadwatch.pipeline import RoadWatchService


def test_metrics_keep_processing_and_display_fps_separate() -> None:
    metrics = MetricsCollector()
    metrics.finish_warmup()
    metrics.mark_processing_started()
    metrics.processed_frames = 4
    metrics.record_display_frame()
    metrics.record_display_frame()
    metrics.record_display_drop()
    snapshot = metrics.snapshot()

    assert snapshot["processed_frames"] == 4
    assert snapshot["display_frames"] == 2
    assert snapshot["display_dropped_frames"] == 1
    assert snapshot["processed_fps"] > 0
    assert snapshot["display_fps"] > 0


def test_performance_settings_have_safe_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_STREAM_FPS", "24")
    monkeypatch.setenv("ROADWATCH_STREAM_JPEG_QUALITY", "65")
    monkeypatch.setenv("ROADWATCH_STREAM_MAX_WIDTH", "960")
    monkeypatch.setenv("ROADWATCH_PUBLISH_SKIPPED_FRAMES", "0")
    monkeypatch.setenv("ROADWATCH_ASYNC_OPTIONAL", "1")
    config = ConfigManager().snapshot()

    assert config["app"]["stream_fps"] == 24.0
    assert config["app"]["stream_jpeg_quality"] == 65
    assert config["app"]["stream_max_width"] == 960
    assert config["app"]["publish_skipped_frames"] is False
    assert config["inference"]["async_optional_perception"] is True


def test_annotate_accepts_display_frame_without_lane_state() -> None:
    frame = np.zeros((32, 48, 3), dtype=np.uint8)
    result = RoadWatchService._annotate(frame, [], [], None, {}, [])
    assert result.shape == frame.shape
