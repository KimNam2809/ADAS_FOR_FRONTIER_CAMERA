"""Deterministic traffic-density context for alert routing.

The context engine is deliberately conservative.  It does not create a new
perception signal and it never emits an actuator command; it only decides
whether already-confirmed road users justify the dense-traffic audio policy.
"""

from __future__ import annotations

import math
import os
from collections import deque
from typing import Any, Iterable


VALID_MODES = {"off", "shadow", "enforce"}
ROAD_USER_LABELS = {
    "person",
    "pedestrian",
    "rider",
    "bicycle",
    "bike",
    "cyclist",
    "motorcycle",
    "motorbike",
    "car",
    "vehicle",
    "bus",
    "truck",
}
TWO_WHEELER_LABELS = {
    "bicycle",
    "bike",
    "cyclist",
    "motorcycle",
    "motorbike",
    "rider",
}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def _label(track: dict[str, Any]) -> str:
    return str(
        track.get("class_name")
        or track.get("label")
        or track.get("name")
        or ""
    ).strip().lower().replace("_", " ")


class TrafficContextEngine:
    """Estimate normal/dense traffic with bounded memory and hysteresis."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        section = dict((config or {}).get("traffic_context", {}))
        requested = os.getenv("ROADWATCH_TRAFFIC_CONTEXT_MODE", section.get("mode", "off"))
        self.mode = str(requested).strip().lower()
        if self.mode not in VALID_MODES:
            self.mode = "off"
        self.config = section
        self.history: deque[bool] = deque(maxlen=5)
        self._dense = False
        self._below_threshold_since: float | None = None
        self._last_context_beep: float = float("-inf")
        self._last_error: str | None = None
        self._last_state = self._normal()

    def reset(self) -> None:
        self.history.clear()
        self._dense = False
        self._below_threshold_since = None
        self._last_context_beep = float("-inf")
        self._last_error = None
        self._last_state = self._normal()

    def _normal(self, error: str | None = None) -> dict[str, Any]:
        return {
            "mode": "normal",
            "risk_state": "calm",
            "density_score": 0.0,
            "confirmed_road_users": 0,
            "two_wheeler_count": 0,
            "road_occupancy": 0.0,
            "low_motion_ratio": 0.0,
            "audio_policy": "normal",
            "policy_mode": self.mode,
            "attention_due": False,
            "transition": None,
            "fallback": bool(error),
            "error": error,
        }

    @staticmethod
    def _is_eligible(track: dict[str, Any], frame_height: int) -> bool:
        if not bool(track.get("confirmed", False)):
            return False
        if _as_float(track.get("age_seconds")) < 0.5:
            return False
        label = _label(track)
        if label not in ROAD_USER_LABELS:
            return False
        # The risk engine marks sidewalk-only people as neither drivable nor
        # path-relevant.  Requiring one of these flags avoids turning a busy
        # sidewalk into a dense-road context.
        road_relevant = any(
            bool(track.get(key, False))
            for key in ("on_drivable", "in_ego_lane", "path_conflict", "near_field_threat")
        )
        if not road_relevant:
            return False
        bbox = track.get("bbox")
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            bottom = _as_float(bbox[3])
            if frame_height > 0 and bottom < frame_height * 0.45:
                return False
        return True

    @staticmethod
    def _occupancy(tracks: Iterable[dict[str, Any]], frame_shape: tuple[int, int]) -> float:
        height, width = frame_shape
        if height <= 0 or width <= 0:
            return 0.0
        roi_area = float(width * height * 0.55)
        total = 0.0
        for track in tracks:
            bbox = track.get("bbox")
            if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                continue
            x1, y1, x2, y2 = (_as_float(value) for value in bbox)
            total += max(0.0, min(width, x2) - max(0.0, x1)) * max(
                0.0, min(height, y2) - max(height * 0.45, y1)
            )
        return min(1.0, total / max(roi_area, 1.0))

    def update(
        self,
        tracks: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        frame_shape: tuple[int, int],
        source_time: float,
    ) -> dict[str, Any]:
        """Return an auditable context snapshot for the current inference frame."""

        if self.mode == "off":
            self.history.clear()
            self._dense = False
            self._below_threshold_since = None
            self._last_state = self._normal()
            return dict(self._last_state)

        try:
            frame_height = int(frame_shape[0]) if frame_shape else 0
            eligible = [track for track in tracks if self._is_eligible(track, frame_height)]
            unique: dict[str, dict[str, Any]] = {}
            for index, track in enumerate(eligible):
                key = str(track.get("track_id", track.get("id", index)))
                unique.setdefault(key, track)
            eligible = list(unique.values())
            count = len(eligible)
            two_wheelers = sum(1 for track in eligible if _label(track) in TWO_WHEELER_LABELS)
            low_motion = [
                track
                for track in eligible
                if abs(_as_float(track.get("lateral_velocity"))) < 0.05
                and abs(_as_float(track.get("expansion_rate"))) < 0.10
                and abs(_as_float(track.get("relative_closing_rate_per_s"))) < 0.10
            ]
            low_motion_ratio = len(low_motion) / count if count else 0.0
            occupancy = self._occupancy(eligible, frame_shape)
            enter_count = int(self.config.get("enter_count", 8))
            mixed_count = int(self.config.get("mixed_count", 6))
            mixed_two_wheelers = int(self.config.get("mixed_two_wheeler_count", 2))
            qualifying = count >= enter_count or (
                count >= mixed_count and two_wheelers >= mixed_two_wheelers
            )
            self.history.append(qualifying)
            stable_enter = sum(self.history) >= int(self.config.get("enter_frames", 3))
            source_clock = _as_float(source_time)
            transition: str | None = None
            attention_due = False
            if not self._dense and stable_enter:
                self._dense = True
                self._below_threshold_since = None
                transition = "normal_to_dense"
                cooldown = _as_float(self.config.get("context_beep_cooldown_seconds", 30.0), 30.0)
                attention_due = source_clock - self._last_context_beep >= cooldown
                if attention_due:
                    self._last_context_beep = source_clock
            elif self._dense:
                exit_count = int(self.config.get("exit_count", 5))
                if count < exit_count:
                    if self._below_threshold_since is None:
                        self._below_threshold_since = source_clock
                    exit_seconds = _as_float(self.config.get("exit_seconds", 2.0), 2.0)
                    if source_clock - self._below_threshold_since >= exit_seconds:
                        self._dense = False
                        self.history.clear()
                        self._below_threshold_since = None
                        transition = "dense_to_normal"
                else:
                    self._below_threshold_since = None

            threat = any(
                str(item.get("severity")) == "critical"
                or _as_float(item.get("risk_score")) >= 0.72
                or bool((item.get("evidence") or {}).get("near_field_imminent"))
                or bool((item.get("evidence") or {}).get("emergency_near_field"))
                for item in candidates
            )
            state = {
                "mode": "dense" if self._dense else "normal",
                "risk_state": "threat" if threat else "calm",
                "density_score": round(
                    min(1.0, (count / max(enter_count, 1)) * 0.6 + two_wheelers / max(enter_count, 1) * 0.25 + occupancy * 0.15),
                    4,
                ),
                "confirmed_road_users": count,
                "two_wheeler_count": two_wheelers,
                "road_occupancy": round(occupancy, 4),
                "low_motion_ratio": round(low_motion_ratio, 4),
                "audio_policy": "dense_selective" if self._dense and self.mode == "enforce" else "normal",
                "policy_mode": self.mode,
                "attention_due": attention_due and not threat and self._dense and self.mode == "enforce",
                "transition": transition,
                "fallback": False,
                "error": self._last_error,
            }
            self._last_error = None
            self._last_state = state
            return dict(state)
        except Exception as exc:  # fail-safe: do not change existing audio policy
            self._last_error = str(exc)[:300]
            self.reset()
            self._last_error = str(exc)[:300]
            self._last_state = self._normal(self._last_error)
            return dict(self._last_state)

    def snapshot(self) -> dict[str, Any]:
        """Return the last context without advancing hysteresis."""

        return dict(self._last_state)
