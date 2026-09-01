from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any


SEMANTIC_FAMILIES = {
    "car": "motor_vehicle",
    "bus": "motor_vehicle",
    "truck": "motor_vehicle",
    "rider": "two_wheeler",
    "bicycle": "two_wheeler",
    "motorcycle": "two_wheeler",
}


def semantic_family(label: str) -> str:
    return SEMANTIC_FAMILIES.get(label, label)


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
    label_votes: dict[str, float] = field(default_factory=dict)
    label_history: deque[tuple[str, float]] = field(
        default_factory=lambda: deque(maxlen=5)
    )
    expansion_ema: float = 0.0
    lateral_ema: float = 0.0

    def predicted_bbox(self) -> list[float]:
        if len(self.history) < 2:
            return list(self.bbox)
        _, old = self.history[-2]
        _, new = self.history[-1]
        dx = ((new[0] + new[2]) - (old[0] + old[2])) * 0.5
        dy = ((new[1] + new[3]) - (old[1] + old[3])) * 0.5
        return [new[0] + dx, new[1] + dy, new[2] + dx, new[3] + dy]

    def update(self, detection: dict[str, Any], timestamp: float) -> None:
        self.bbox = detection["bbox"]
        self.confidence = detection["confidence"]
        self.last_seen = timestamp
        self.hits += 1
        self.missed = 0
        self.history.append((timestamp, list(self.bbox)))
        label = str(detection["label"])
        self.label_history.append((label, float(detection["confidence"])))
        rolling_votes: dict[str, float] = {}
        for observed_label, confidence in self.label_history:
            rolling_votes[observed_label] = rolling_votes.get(observed_label, 0.0) + confidence
        self.label_votes = rolling_votes
        stable_label = max(rolling_votes, key=rolling_votes.get)
        self.label = stable_label
        if stable_label == label:
            self.class_id = int(detection["class_id"])

    def motion(self, frame_width: int) -> tuple[float, float]:
        if len(self.history) < 2:
            return 0.0, 0.0
        recent = list(self.history)[-8:]
        t0 = recent[0][0]
        times = [item[0] - t0 for item in recent]
        if times[-1] < 0.50:
            return 0.0, 0.0
        log_scales = []
        centers = []
        for _, box in recent:
            area = max((box[2] - box[0]) * (box[3] - box[1]), 1.0)
            log_scales.append(math.log(math.sqrt(area)))
            centers.append(((box[0] + box[2]) * 0.5) / max(frame_width, 1))

        def slope(values: list[float]) -> float:
            mean_t = sum(times) / len(times)
            mean_v = sum(values) / len(values)
            denominator = sum((value - mean_t) ** 2 for value in times)
            if denominator <= 1e-9:
                return 0.0
            return sum(
                (time_value - mean_t) * (value - mean_v)
                for time_value, value in zip(times, values)
            ) / denominator

        expansion = max(-2.0, min(2.0, slope(log_scales)))
        lateral = max(-1.0, min(1.0, slope(centers)))
        alpha = 0.65
        self.expansion_ema = alpha * expansion + (1.0 - alpha) * self.expansion_ema
        self.lateral_ema = alpha * lateral + (1.0 - alpha) * self.lateral_ema
        return float(self.expansion_ema), float(self.lateral_ema)


class IoUTracker:
    """Deterministic lightweight tracker used to create temporal evidence."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.iou_threshold = float(config["iou_threshold"])
        self.max_missed = int(config["max_missed"])
        self.confirmation_hits = int(config["confirmation_hits"])
        self.history_size = int(config["history_size"])
        self.semantic_family_matching = bool(config.get("semantic_family_matching", True))
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
                same_class = track.class_id == int(detection["class_id"])
                same_family = (
                    self.semantic_family_matching
                    and semantic_family(track.label)
                    == semantic_family(str(detection["label"]))
                )
                if same_class or same_family:
                    score = bbox_iou(track.predicted_bbox(), detection["bbox"])
                    if score >= self.iou_threshold:
                        candidates.append((score, track_id, index))
                    else:
                        predicted = track.predicted_bbox()
                        pcx = (predicted[0] + predicted[2]) * 0.5
                        pcy = (predicted[1] + predicted[3]) * 0.5
                        box = detection["bbox"]
                        dcx = (box[0] + box[2]) * 0.5
                        dcy = (box[1] + box[3]) * 0.5
                        distance = math.hypot(dcx - pcx, dcy - pcy) / max(frame_width, 1)
                        old_width = max(predicted[2] - predicted[0], 1.0)
                        new_width = max(box[2] - box[0], 1.0)
                        size_ratio = min(old_width, new_width) / max(old_width, new_width)
                        distance_gate = min(0.16, 0.08 + track.missed * 0.025)
                        if distance <= distance_gate and size_ratio >= 0.45:
                            candidates.append(
                                (0.20 - distance + 0.05 * size_ratio, track_id, index)
                            )
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
                label_votes={str(detection["label"]): float(detection["confidence"])},
                label_history=deque(
                    [(str(detection["label"]), float(detection["confidence"]))],
                    maxlen=5,
                ),
            )
            track.history.append((timestamp, list(track.bbox)))
            self._tracks[self._next_id] = track
            self._next_id += 1

        result: list[dict[str, Any]] = []
        for track in self._tracks.values():
            if track.missed:
                continue
            expansion, lateral = track.motion(frame_width)
            first_box = track.history[0][1]
            first_x_norm = (
                (first_box[0] + first_box[2]) * 0.5 / max(frame_width, 1)
            )
            current_x_norm = (
                (track.bbox[0] + track.bbox[2]) * 0.5 / max(frame_width, 1)
            )
            first_y_norm = (
                (first_box[1] + first_box[3]) * 0.5 / max(frame_width, 1)
            )
            current_y_norm = (
                (track.bbox[1] + track.bbox[3]) * 0.5 / max(frame_width, 1)
            )
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
                    "origin_x_norm": round(first_x_norm, 4),
                    "displacement_x_norm": round(current_x_norm - first_x_norm, 4),
                    "displacement_y_norm": round(current_y_norm - first_y_norm, 4),
                    "motion_observations": len(track.history),
                }
            )
        return result
