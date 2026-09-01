import numpy as np

from scripts.ingest_dashcam import frame_metrics, select_temporally_stratified


def test_frame_metrics_assigns_light_condition() -> None:
    dark = np.full((120, 200, 3), 20, dtype=np.uint8)
    bright = np.full((120, 200, 3), 140, dtype=np.uint8)
    dark_metrics, dark_gray = frame_metrics(dark, None)
    bright_metrics, _ = frame_metrics(bright, dark_gray)
    assert dark_metrics["auto_light_condition"] == "night"
    assert bright_metrics["auto_light_condition"] == "day"
    assert bright_metrics["scene_delta"] > 0


def test_temporal_selection_covers_beginning_and_end() -> None:
    samples = [
        {"sample_id": index, "timestamp_s": float(index), "quality_score": (index % 7) / 7}
        for index in range(100)
    ]
    selected = select_temporally_stratified(samples, 10)
    assert len(selected) == 10
    assert len({item["sample_id"] for item in selected}) == 10
    assert selected[0]["timestamp_s"] < 10
    assert selected[-1]["timestamp_s"] > 90
