from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


REFERENCE_HEIGHT_M = {
    "person": 1.70,
    "rider": 1.55,
    "bicycle": 1.45,
    "motorcycle": 1.45,
    "car": 1.50,
    "bus": 3.10,
    "truck": 3.10,
}


class MonocularKinematics:
    """Calibration-gated telemetry estimator; it never controls the vehicle.

    Bounding-box ranging is class-prior based, so outputs remain advisory and
    are not allowed to trigger FCW until validated on a measured closed course.
    """

    def __init__(self, calibration_path: Path, enabled: bool = False) -> None:
        self.calibration_path = calibration_path
        self.calibration: dict[str, Any] = {}
        self.enabled = False
        self._history: dict[int, deque[tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=8)
        )
        if enabled and calibration_path.exists():
            candidate = json.loads(calibration_path.read_text(encoding="utf-8"))
            if bool(candidate.get("calibrated")) and float(candidate.get("fy", 0)) > 0:
                self.calibration = candidate
                self.enabled = True

    def reset(self) -> None:
        self._history.clear()

    def enrich(self, tracks: list[dict[str, Any]], timestamp: float) -> list[dict[str, Any]]:
        if not self.enabled:
            for track in tracks:
                track["metric_ttc_available"] = False
            return tracks
        fy = float(self.calibration["fy"])
        rms = float(self.calibration.get("rms_reprojection_error", 2.0))
        calibration_confidence = max(0.2, min(1.0, 1.0 - rms / 3.0))
        active_ids: set[int] = set()
        for track in tracks:
            track_id = int(track["track_id"])
            active_ids.add(track_id)
            reference_height = REFERENCE_HEIGHT_M.get(str(track["label"]))
            bbox = track["bbox"]
            pixel_height = max(float(bbox[3]) - float(bbox[1]), 1.0)
            if reference_height is None or pixel_height < 12:
                track["metric_ttc_available"] = False
                continue
            distance = reference_height * fy / pixel_height
            history = self._history[track_id]
            history.append((float(timestamp), distance))
            closing_speed = 0.0
            ttc: float | None = None
            if len(history) >= 3:
                old_t, old_distance = history[0]
                dt = max(float(timestamp) - old_t, 1e-3)
                closing_speed = max(0.0, (old_distance - distance) / dt)
                if closing_speed >= 0.5:
                    ttc = distance / closing_speed
            track.update(
                {
                    "metric_ttc_available": ttc is not None,
                    "distance_m": round(distance, 2),
                    "closing_speed_mps": round(closing_speed, 2),
                    "ttc_seconds": None if ttc is None else round(min(ttc, 99.0), 2),
                    "metric_ttc_confidence": round(
                        calibration_confidence * min(1.0, pixel_height / 120.0), 3
                    ),
                    "metric_ttc_role": "telemetry_only",
                }
            )
        for track_id in list(self._history):
            if track_id not in active_ids:
                del self._history[track_id]
        return tracks

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "calibration": str(self.calibration_path),
            "role": "telemetry_only",
            "validated_for_alerting": False,
        }
