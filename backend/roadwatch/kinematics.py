from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from .calibration import load_valid_calibration


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
        self.calibration_errors: list[str] = []
        self._history: dict[int, deque[tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=8)
        )
        self._image_history: dict[int, deque[tuple[float, float]]] = defaultdict(
            lambda: deque(maxlen=8)
        )
        if enabled and calibration_path.exists():
            candidate, errors = load_valid_calibration(calibration_path)
            self.calibration_errors = errors
            if not errors:
                self.calibration = candidate
                self.enabled = True
        elif enabled:
            self.calibration_errors = ["calibration artifact does not exist"]

    def reset(self) -> None:
        self._history.clear()
        self._image_history.clear()

    @staticmethod
    def _slope(samples: list[tuple[float, float]]) -> float:
        if len(samples) < 3 or samples[-1][0] - samples[0][0] < 0.25:
            return 0.0
        mean_t = statistics.fmean(item[0] for item in samples)
        mean_v = statistics.fmean(item[1] for item in samples)
        denominator = sum((time_value - mean_t) ** 2 for time_value, _ in samples)
        if denominator <= 1e-9:
            return 0.0
        return sum(
            (time_value - mean_t) * (value - mean_v)
            for time_value, value in samples
        ) / denominator

    def _enrich_image_space(self, track: dict[str, Any], timestamp: float) -> None:
        track_id = int(track["track_id"])
        bbox = track["bbox"]
        pixel_height = max(float(bbox[3]) - float(bbox[1]), 1.0)
        history = self._image_history[track_id]
        prior_rate = self._slope(list(history)[-5:])
        history.append((float(timestamp), math.log(pixel_height)))
        closing_rate = max(-3.0, min(3.0, self._slope(list(history)[-6:])))
        recent_rate = self._slope(list(history)[-3:])
        acceleration = max(-6.0, min(6.0, (recent_rate - prior_rate) * 2.0))
        proxy_ttc = 1.0 / closing_rate if closing_rate >= 0.05 else None
        track.update(
            {
                "kinematics_space": "image_space",
                "relative_scale_px": round(pixel_height, 2),
                "relative_closing_rate_per_s": round(closing_rate, 4),
                "relative_closing_acceleration_per_s2": round(acceleration, 4),
                "relative_ttc_proxy_seconds": (
                    None if proxy_ttc is None else round(min(proxy_ttc, 99.0), 2)
                ),
                "relative_kinematics_role": "advisory_image_space_only",
                "relative_kinematics_observations": len(history),
            }
        )

    def enrich(self, tracks: list[dict[str, Any]], timestamp: float) -> list[dict[str, Any]]:
        active_ids: set[int] = set()
        for track in tracks:
            active_ids.add(int(track["track_id"]))
            self._enrich_image_space(track, timestamp)
            track["metric_ttc_available"] = False
        for track_id in list(self._image_history):
            if track_id not in active_ids:
                del self._image_history[track_id]
        if not self.enabled:
            return tracks
        fy = float(self.calibration["fy"])
        rms = float(self.calibration.get("rms_reprojection_error", 2.0))
        calibration_confidence = max(0.2, min(1.0, 1.0 - rms / 3.0))
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
            "relative_kinematics": "image_space_only",
            "calibration_errors": self.calibration_errors,
        }
