from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any


def bbox_iou(a: list[float], b: list[float]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    return intersection / max(area_a + area_b - intersection, 1e-6)


@dataclass
class Track:
    track_id: int
    label: str
    class_id: int
    bbox: list[float]
    confidence: float
    first_seen: float
    last_seen: float
    hits: int = 1
    missed: int = 0
    history: deque[tuple[float, list[float]]] = field(default_factory=lambda: deque(maxlen=12))

    def update(self, detection: dict[str, Any], timestamp: float) -> None:
        self.bbox = detection["bbox"]
        self.confidence = detection["confidence"]
        self.last_seen = timestamp
        self.hits += 1
        self.missed = 0
        self.history.append((timestamp, list(self.bbox)))

    def motion(self, frame_width: int) -> tuple[float, float]:
        if len(self.history) < 2:
            return 0.0, 0.0
        old_t, old_box = self.history[0]
        new_t, new_box = self.history[-1]
        dt = max(new_t - old_t, 1e-3)
        # Short tracks are dominated by detector-box jitter. Do not turn that
        # into a fake closing-speed signal.
        if dt < 0.30:
            return 0.0, 0.0
        old_area = max((old_box[2] - old_box[0]) * (old_box[3] - old_box[1]), 1.0)
        new_area = max((new_box[2] - new_box[0]) * (new_box[3] - new_box[1]), 1.0)
        expansion = (math.sqrt(new_area) / math.sqrt(old_area) - 1.0) / dt
        old_center = (old_box[0] + old_box[2]) * 0.5
        new_center = (new_box[0] + new_box[2]) * 0.5
        lateral = ((new_center - old_center) / max(frame_width, 1)) / dt
        return float(expansion), float(lateral)


class IoUTracker:
    """Deterministic lightweight tracker used to create temporal evidence."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.iou_threshold = float(config["iou_threshold"])
        self.max_missed = int(config["max_missed"])
        self.confirmation_hits = int(config["confirmation_hits"])
        self.history_size = int(config["history_size"])
        self._next_id = 1
        self._tracks: dict[int, Track] = {}

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1

    def update(
        self, detections: list[dict[str, Any]], timestamp: float, frame_width: int
    ) -> list[dict[str, Any]]:
        unmatched_detections = set(range(len(detections)))
        unmatched_tracks = set(self._tracks)
        candidates: list[tuple[float, int, int]] = []
        for track_id, track in self._tracks.items():
            for index, detection in enumerate(detections):
                if track.class_id == int(detection["class_id"]):
                    score = bbox_iou(track.bbox, detection["bbox"])
                    if score >= self.iou_threshold:
                        candidates.append((score, track_id, index))
        for _, track_id, index in sorted(candidates, reverse=True):
            if track_id not in unmatched_tracks or index not in unmatched_detections:
                continue
            self._tracks[track_id].update(detections[index], timestamp)
            unmatched_tracks.remove(track_id)
            unmatched_detections.remove(index)

        for track_id in unmatched_tracks:
            self._tracks[track_id].missed += 1
        for track_id in list(self._tracks):
            if self._tracks[track_id].missed > self.max_missed:
                del self._tracks[track_id]

        for index in unmatched_detections:
            detection = detections[index]
            track = Track(
                track_id=self._next_id,
                label=detection["label"],
                class_id=int(detection["class_id"]),
                bbox=list(detection["bbox"]),
                confidence=float(detection["confidence"]),
                first_seen=timestamp,
                last_seen=timestamp,
                history=deque(maxlen=self.history_size),
            )
            track.history.append((timestamp, list(track.bbox)))
            self._tracks[self._next_id] = track
            self._next_id += 1

        result: list[dict[str, Any]] = []
        for track in self._tracks.values():
            if track.missed:
                continue
            expansion, lateral = track.motion(frame_width)
            result.append(
                {
                    "track_id": track.track_id,
                    "label": track.label,
                    "class_id": track.class_id,
                    "bbox": track.bbox,
                    "confidence": round(track.confidence, 4),
                    "hits": track.hits,
                    "confirmed": track.hits >= self.confirmation_hits,
                    "age_seconds": round(timestamp - track.first_seen, 2),
                    "expansion_rate": round(expansion, 4),
                    "lateral_velocity": round(lateral, 4),
                }
            )
        return result
