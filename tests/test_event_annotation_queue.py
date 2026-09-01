from scripts.build_event_annotation_queue import choose_windows


def test_annotation_windows_cover_target_without_overlap() -> None:
    samples = [
        {
            "timestamp_s": index * 2.0,
            "scene_delta": index % 11,
            "quality_score": 0.8,
            "file": f"frame-{index}.jpg",
            "auto_light_condition": "day",
        }
        for index in range(1200)
    ]
    windows = choose_windows(samples, duration=2400.0, count=60, window_seconds=10.0)
    assert len(windows) == 60
    assert sum(item["coverage_seconds"] for item in windows) == 600.0
    assert all(left["end_seconds"] <= right["start_seconds"] for left, right in zip(windows, windows[1:]))
    assert all(item["primary_review"]["status"] == "pending" for item in windows)


def test_short_video_caps_windows_and_applies_unique_prefix() -> None:
    samples = [
        {
            "timestamp_s": float(index),
            "scene_delta": index,
            "quality_score": 0.5,
            "file": f"short-{index}.jpg",
            "auto_light_condition": "night",
        }
        for index in range(25)
    ]

    windows = choose_windows(
        samples,
        duration=25.0,
        count=60,
        window_seconds=10.0,
        window_prefix="rw05-night",
    )

    assert len(windows) == 2
    assert [item["window_id"] for item in windows] == [
        "rw05-night-001",
        "rw05-night-002",
    ]
    assert windows[0]["end_seconds"] <= windows[1]["start_seconds"]
