from roadwatch.tracking import IoUTracker, bbox_iou


CONFIG = {"iou_threshold": 0.2, "max_missed": 2, "confirmation_hits": 2, "history_size": 8}


def detection(box: list[float]) -> dict:
    return {"bbox": box, "class_id": 3, "label": "motorcycle", "confidence": 0.9}


def test_iou() -> None:
    assert bbox_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert bbox_iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0


def test_tracker_confirms_temporal_detection() -> None:
    tracker = IoUTracker(CONFIG)
    first = tracker.update([detection([100, 100, 180, 220])], 1.0, 640)
    second = tracker.update([detection([98, 98, 185, 230])], 1.5, 640)
    assert first[0]["confirmed"] is False
    assert second[0]["confirmed"] is True
    assert second[0]["track_id"] == first[0]["track_id"]
    assert second[0]["expansion_rate"] > 0


def test_two_wheeler_class_switch_keeps_track_and_stable_label() -> None:
    tracker = IoUTracker(CONFIG)
    rider = {"bbox": [100, 100, 180, 220], "class_id": 1, "label": "rider", "confidence": 0.9}
    motorcycle = {
        "bbox": [102, 101, 183, 222],
        "class_id": 3,
        "label": "motorcycle",
        "confidence": 0.7,
    }
    first = tracker.update([rider], 1.0, 640)
    second = tracker.update([motorcycle], 1.5, 640)
    assert second[0]["track_id"] == first[0]["track_id"]
    assert second[0]["label"] == "rider"
    assert second[0]["confirmed"] is True
