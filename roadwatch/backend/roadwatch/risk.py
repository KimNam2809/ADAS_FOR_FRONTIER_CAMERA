from __future__ import annotations

import math
import re
import time
from collections import defaultdict
from typing import Any

import numpy as np


VI_LABELS = {
    "person": "Người đi bộ",
    "bicycle": "Xe đạp",
    "motorcycle": "Xe máy",
    "car": "Ô tô",
    "bus": "Xe buýt",
    "truck": "Xe tải",
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(value, high))


def _fit_ego_lane(lane_mask: np.ndarray) -> dict[str, Any]:
    height, width = lane_mask.shape
    center = width * 0.5
    rows: list[tuple[float, float, float]] = []
    step = max(2, height // 120)
    for y in range(int(height * 0.30), int(height * 0.90), step):
        xs = np.flatnonzero(lane_mask[y] > 0)
        left = xs[xs < center]
        right = xs[xs > center]
        if left.size and right.size:
            rows.append((float(y), float(left.max()), float(right.min())))
    if len(rows) < 6:
        return {"quality": 0.0, "left": None, "right": None, "offset": 0.0}
    data = np.asarray(rows)
    left_poly = np.polyfit(data[:, 0], data[:, 1], 2)
    right_poly = np.polyfit(data[:, 0], data[:, 2], 2)
    y_eval = min(height * 0.86, float(data[:, 0].max()) + height * 0.12)
    left = float(np.polyval(left_poly, y_eval))
    right = float(np.polyval(right_poly, y_eval))
    lane_width = right - left
    plausible = 0.22 * width <= lane_width <= 0.92 * width
    coverage = _clamp(len(rows) / 12.0)
    quality = coverage if plausible else coverage * 0.25
    lane_center = (left + right) * 0.5
    offset = (center - lane_center) / max(lane_width * 0.5, 1.0)
    return {
        "quality": round(quality, 4),
        "left": round(left, 1),
        "right": round(right, 1),
        "offset": round(float(offset), 4),
        "width_px": round(lane_width, 1),
        "left_poly": left_poly.tolist(),
        "right_poly": right_poly.tolist(),
    }


class RiskEngine:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config["risk"]
        self.tracking_config = config["tracking"]
        self._ldw_streak = 0
        self._sign_hits: dict[int, int] = defaultdict(int)
        self._sign_last_seen: dict[int, float] = {}

    def reset(self) -> None:
        self._ldw_streak = 0
        self._sign_hits.clear()
        self._sign_last_seen.clear()

    def analyze(
        self,
        tracks: list[dict[str, Any]],
        signs: list[dict[str, Any]],
        lane_output: dict[str, Any],
        frame_shape: tuple[int, int],
        sign_fresh: bool,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        height, width = frame_shape
        lane = _fit_ego_lane(lane_output["lane_mask"])
        lane["geometry_quality"] = lane["quality"]
        lane["segmentation_quality"] = round(float(lane_output.get("quality", 0.0)), 4)
        lane["quality"] = round(
            min(lane["geometry_quality"], lane["segmentation_quality"]), 4
        )
        drivable = lane_output["drivable_mask"]
        candidates: list[dict[str, Any]] = []
        enriched: list[dict[str, Any]] = []

        for track in tracks:
            x1, y1, x2, y2 = track["bbox"]
            cx, cy = (x1 + x2) * 0.5, (y1 + y2) * 0.5
            sample_x = int(_clamp(cx / width) * (width - 1))
            sample_y = int(_clamp(y2 / height) * (height - 1))
            on_drivable = bool(drivable[sample_y, sample_x]) if drivable.size else False
            if lane["left"] is not None:
                y_for_lane = _clamp(sample_y, height * 0.48, height * 0.95)
                left = float(np.polyval(lane["left_poly"], y_for_lane))
                right = float(np.polyval(lane["right_poly"], y_for_lane))
                in_ego_lane = left <= cx <= right
            else:
                in_ego_lane = 0.38 * width <= cx <= 0.62 * width

            x_norm = cx / width
            location = "phía trước"
            if x_norm < 0.40:
                location = "phía trước bên trái"
            elif x_norm > 0.60:
                location = "phía trước bên phải"
            proximity = _clamp((y2 / height - 0.38) / 0.58)
            center_score = _clamp(1.0 - abs(x_norm - 0.5) * 2.2)
            approach = _clamp(float(track["expansion_rate"]) * 2.5)
            stability = _clamp(float(track["hits"]) / max(self.tracking_config["confirmation_hits"], 1))
            context = 1.0 if in_ego_lane else (0.65 if on_drivable else 0.2)
            risk = (
                0.30 * proximity
                + 0.22 * center_score
                + 0.25 * approach
                + 0.13 * context
                + 0.10 * float(track["confidence"])
            ) * stability
            risk = _clamp(risk)
            item = {
                **track,
                "location": location,
                "on_drivable": on_drivable,
                "in_ego_lane": in_ego_lane,
                "risk_score": round(risk, 4),
                "proximity_score": round(proximity, 4),
                "approaching_score": round(approach, 4),
            }
            enriched.append(item)

            if not track["confirmed"]:
                continue
            evidence = {
                "hits": track["hits"],
                "bbox": [round(float(v), 1) for v in track["bbox"]],
                "in_ego_lane": in_ego_lane,
                "on_drivable": on_drivable,
                "expansion_rate": track["expansion_rate"],
                "lane_quality": lane["quality"],
                "method": "image-space risk; không phải TTC theo mét",
            }
            label_vi = VI_LABELS.get(track["label"], track["label"])
            if (
                track["label"] in {"car", "bus", "truck", "motorcycle", "bicycle"}
                and in_ego_lane
                and (
                    on_drivable
                    or lane["quality"] >= float(self.config["lane_quality_min"])
                )
                and proximity >= 0.12
                and float(track["age_seconds"]) >= 0.40
                and risk >= float(self.config["fcw_warning"])
            ):
                severity = (
                    "critical"
                    if risk >= float(self.config["fcw_critical"])
                    and track["confidence"] >= float(self.config["critical_confidence_min"])
                    else "warning"
                )
                candidates.append(
                    self._candidate(
                        "fcw",
                        severity,
                        f"{label_vi} {location}, đang tiến gần. Hãy chú ý.",
                        item,
                        evidence,
                    )
                )
            elif (
                track["label"] in {"person", "motorcycle", "bicycle"}
                and on_drivable
                and proximity >= 0.10
                and float(track["age_seconds"]) >= 0.40
                and risk >= float(self.config["vulnerable_warning"])
            ):
                candidates.append(
                    self._candidate(
                        "vulnerable_road_user",
                        "warning",
                        f"{label_vi} {location}, chú ý khoảng cách an toàn.",
                        item,
                        evidence,
                    )
                )

            moving_toward_center = (x_norm < 0.5 and track["lateral_velocity"] > 0.035) or (
                x_norm > 0.5 and track["lateral_velocity"] < -0.035
            )
            if (
                not in_ego_lane
                and on_drivable
                and float(track["age_seconds"]) >= 0.50
                and moving_toward_center
                and risk >= float(self.config["cut_in_warning"])
            ):
                candidates.append(
                    self._candidate(
                        "cut_in",
                        "warning",
                        f"{label_vi} {location} có xu hướng nhập làn.",
                        item,
                        evidence,
                    )
                )

        if lane["quality"] >= float(self.config["lane_quality_min"]):
            if abs(float(lane["offset"])) >= float(self.config["ldw_offset_warning"]):
                self._ldw_streak += 1
            else:
                self._ldw_streak = max(0, self._ldw_streak - 1)
            if self._ldw_streak >= int(self.config["ldw_confirmation_frames"]):
                side = "phải" if lane["offset"] > 0 else "trái"
                candidates.append(
                    {
                        "event_type": "ldw",
                        "severity": "warning",
                        "message": f"Cảnh báo lệch làn bên {side}.",
                        "confidence": lane["quality"],
                        "risk_score": _clamp(abs(float(lane["offset"]))),
                        "object_id": None,
                        "location": side,
                        "cooldown_key": f"ldw:{side}",
                        "evidence": {
                            "lane_offset": lane["offset"],
                            "lane_quality": lane["quality"],
                            "confirmation_frames": self._ldw_streak,
                            "suppression_guard": "lane quality gate",
                        },
                    }
                )
        else:
            self._ldw_streak = 0

        if sign_fresh:
            now = time.time()
            visible_ids = set()
            for sign in signs:
                class_id = int(sign["class_id"])
                visible_ids.add(class_id)
                self._sign_hits[class_id] += 1
                self._sign_last_seen[class_id] = now
                match = re.search(r"Speed limit (\d+)km/h", sign["label"])
                if match and self._sign_hits[class_id] >= int(
                    self.config["speed_sign_confirmation_hits"]
                ):
                    speed = int(match.group(1))
                    candidates.append(
                        {
                            "event_type": "speed_sign",
                            "severity": "advisory",
                            "message": f"Đã nhận diện biển giới hạn tốc độ {speed} ki-lô-mét một giờ.",
                            "confidence": sign["confidence"],
                            "risk_score": 0.25,
                            "object_id": None,
                            "location": "phía trước",
                            "cooldown_key": f"speed_sign:{speed}",
                            "evidence": {
                                "class_id": class_id,
                                "label": sign["label"],
                                "hits": self._sign_hits[class_id],
                                "bbox": sign["bbox"],
                            },
                        }
                    )
            for class_id in list(self._sign_hits):
                if class_id not in visible_ids and now - self._sign_last_seen[class_id] > 2.0:
                    self._sign_hits[class_id] = 0

        return candidates, enriched, lane

    @staticmethod
    def _candidate(
        event_type: str,
        severity: str,
        message: str,
        track: dict[str, Any],
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "event_type": event_type,
            "severity": severity,
            "message": message,
            "confidence": track["confidence"],
            "risk_score": track["risk_score"],
            "object_id": track["track_id"],
            "location": track["location"],
            "cooldown_key": f"{event_type}:{track['track_id']}",
            "evidence": evidence,
        }
