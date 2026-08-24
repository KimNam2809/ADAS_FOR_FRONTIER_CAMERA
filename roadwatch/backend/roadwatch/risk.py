from __future__ import annotations

import math
import statistics
import time
from collections import defaultdict
from typing import Any

import cv2
import numpy as np

from .tracking import bbox_iou, semantic_family
from .signs import policy_for_label, speed_value


VI_LABELS = {
    "person": "Người đi bộ",
    "rider": "Người đi xe hai bánh",
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
    if not plausible:
        return {
            "quality": 0.0,
            "left": None,
            "right": None,
            "offset": 0.0,
            "width_px": None,
            "rejection_reason": "invalid_lane_boundary_order_or_width",
        }
    quality = coverage
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
        self._sign_first_seen: dict[int, float] = {}
        self._sign_first_bbox: dict[int, list[float]] = {}
        self._sign_last_bbox: dict[int, list[float]] = {}
        self._active_speed_class: int | None = None
        self._braking_streak: dict[int, int] = defaultdict(int)
        self._lane_offset_ema: float | None = None
        self._fcw_armed: dict[int, bool] = defaultdict(lambda: True)
        self._fcw_last_severity: dict[int, str] = {}
        self._critical_fcw_tracks: set[int] = set()
        self._signal_streak: dict[tuple[int, str], int] = defaultdict(int)
        self._signal_last_frame: dict[tuple[int, str], int] = {}
        self._analysis_frame = 0
        self.last_sign_trace: list[dict[str, Any]] = []

    def reset(self) -> None:
        self._ldw_streak = 0
        self._sign_hits.clear()
        self._sign_last_seen.clear()
        self._sign_first_seen.clear()
        self._sign_first_bbox.clear()
        self._sign_last_bbox.clear()
        self._active_speed_class = None
        self._braking_streak.clear()
        self._lane_offset_ema = None
        self._fcw_armed.clear()
        self._fcw_last_severity.clear()
        self._critical_fcw_tracks.clear()
        self._signal_streak.clear()
        self._signal_last_frame.clear()
        self._analysis_frame = 0
        self.last_sign_trace = []

    def analyze(
        self,
        tracks: list[dict[str, Any]],
        signs: list[dict[str, Any]],
        lane_output: dict[str, Any],
        frame_shape: tuple[int, int],
        sign_fresh: bool,
        frame: np.ndarray | None = None,
        timestamp: float | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        self._analysis_frame += 1
        height, width = frame_shape
        lane = _fit_ego_lane(lane_output["lane_mask"])
        lane["geometry_quality"] = lane["quality"]
        lane["segmentation_quality"] = round(float(lane_output.get("quality", 0.0)), 4)
        lane["quality"] = round(
            min(lane["geometry_quality"], lane["segmentation_quality"]), 4
        )
        if lane["quality"] >= float(self.config["lane_quality_min"]):
            alpha = float(self.config.get("lane_offset_smoothing_alpha", 0.35))
            raw_offset = float(lane["offset"])
            self._lane_offset_ema = (
                raw_offset
                if self._lane_offset_ema is None
                else alpha * raw_offset + (1.0 - alpha) * self._lane_offset_ema
            )
            lane["raw_offset"] = round(raw_offset, 4)
            lane["offset"] = round(self._lane_offset_ema, 4)
        else:
            self._lane_offset_ema = None
        drivable = lane_output["drivable_mask"]
        candidates: list[dict[str, Any]] = []
        enriched: list[dict[str, Any]] = []
        stable_lateral = [
            float(track.get("lateral_velocity", 0.0))
            for track in tracks
            if track.get("confirmed") and int(track.get("motion_observations", 0)) >= 4
        ]
        # One or two tracks may themselves be the crossing threat. Treating
        # their motion as ego-camera motion would cancel the signal entirely.
        global_lateral_velocity = (
            statistics.median(stable_lateral) if len(stable_lateral) >= 3 else 0.0
        )
        stable_displacements = [
            float(track.get("displacement_x_norm", 0.0))
            for track in tracks
            if track.get("confirmed") and int(track.get("motion_observations", 0)) >= 4
        ]
        global_lateral_displacement = (
            statistics.median(stable_displacements)
            if len(stable_displacements) >= 3
            else 0.0
        )

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
            relative_lateral = float(track["lateral_velocity"]) - global_lateral_velocity
            relative_displacement = (
                float(track.get("displacement_x_norm", 0.0))
                - global_lateral_displacement
            )
            vertical_displacement = float(track.get("displacement_y_norm", 0.0))
            motion_observations = int(track.get("motion_observations", 0))
            # Instantaneous box velocity is useful for projection but flips
            # under detector jitter. Direction wording and side-of-origin use
            # the longer trajectory displacement whenever it is meaningful.
            trajectory_lateral = (
                relative_displacement
                if abs(relative_displacement) >= 0.018
                else relative_lateral
            )
            movement_direction = (
                "left_to_right"
                if trajectory_lateral > 0.005
                else "right_to_left"
                if trajectory_lateral < -0.005
                else "longitudinal"
            )
            origin_x_norm = float(track.get("origin_x_norm", x_norm))
            origin_side = (
                "left"
                if origin_x_norm < 0.45
                else "right"
                if origin_x_norm > 0.55
                else "front"
            )
            location = "phía trước"
            if x_norm < 0.40:
                location = "phía trước bên trái"
            elif x_norm > 0.60:
                location = "phía trước bên phải"
            proximity = _clamp((y2 / height - 0.38) / 0.58)
            box_width_ratio = max(0.0, float(x2 - x1)) / max(width, 1)
            center_score = _clamp(1.0 - abs(x_norm - 0.5) * 2.2)
            approach = _clamp(float(track["expansion_rate"]) * 2.5)
            bbox_area_ratio = max(0.0, float(x2 - x1) * float(y2 - y1)) / max(
                width * height, 1
            )
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
            lane_reliable = lane["quality"] >= float(self.config["lane_quality_min"])
            if lane_reliable:
                corridor_left = max(0.05, left / width - 0.04)
                corridor_right = min(0.95, right / width + 0.04)
            else:
                corridor_left, corridor_right = 0.30, 0.70
            horizon = float(self.config.get("trajectory_horizon_seconds", 1.2))
            projected_x_norm = _clamp(x_norm + relative_lateral * horizon)
            path_conflict = (
                corridor_left <= x_norm <= corridor_right
                or corridor_left <= projected_x_norm <= corridor_right
            )
            path_conflict_relaxed = (
                corridor_left - 0.08 <= x_norm <= corridor_right + 0.08
                or corridor_left - 0.08 <= projected_x_norm <= corridor_right + 0.08
            )
            broad_road_zone = 0.12 <= x_norm <= 0.92 and y2 >= height * 0.50
            near_field_vehicle = (
                track["label"] in {"car", "bus", "truck", "motorcycle", "bicycle", "rider"}
                and broad_road_zone
                and proximity >= float(self.config.get("near_field_proximity", 0.48))
                and (
                    approach >= float(self.config.get("near_field_approach_min", 0.015))
                    or abs(relative_lateral)
                    >= float(self.config.get("near_field_lateral_min", 0.018))
                    or box_width_ratio >= float(self.config.get("near_field_width_ratio", 0.18))
                )
            )
            near_field_imminent = near_field_vehicle and (
                approach >= float(self.config.get("near_field_critical_approach", 0.12))
                or (
                    proximity >= float(self.config.get("near_field_critical_proximity", 0.58))
                    and moving_toward_center_hint(x_norm, relative_lateral)
                )
            )
            # Monocular TTC becomes unreliable after ego braking has almost
            # removed relative scale change. A large, persistent object in the
            # ego corridor is therefore an image-space emergency fail-safe.
            # It deliberately makes no claim about distance in metres.
            emergency_near_field = (
                track["label"] in {"car", "bus", "truck", "motorcycle", "bicycle", "rider"}
                and (path_conflict or near_field_imminent)
                and proximity
                >= float(self.config.get("emergency_proximity_min", 0.74))
                and box_width_ratio
                >= float(self.config.get("emergency_width_ratio_min", 0.26))
                and bbox_area_ratio
                >= float(self.config.get("emergency_bbox_area_ratio_min", 0.16))
                and float(track["confidence"])
                >= float(self.config.get("emergency_confidence_min", 0.55))
                and float(track["age_seconds"])
                >= float(self.config.get("emergency_age_seconds_min", 0.40))
            )
            if emergency_near_field:
                risk = max(risk, 0.96)
            elif near_field_imminent:
                risk = max(risk, 0.82)
            elif near_field_vehicle:
                risk = max(risk, 0.64)
            track_id = int(track["track_id"])
            rearm_below = float(self.config["fcw_warning"]) - float(
                self.config.get("fcw_rearm_hysteresis", 0.08)
            )
            if risk < rearm_below:
                self._fcw_armed[track_id] = True
                self._fcw_last_severity.pop(track_id, None)
            item = {
                **track,
                "location": location,
                "on_drivable": on_drivable,
                "in_ego_lane": in_ego_lane,
                "risk_score": round(risk, 4),
                "proximity_score": round(proximity, 4),
                "approaching_score": round(approach, 4),
                "near_field_threat": near_field_vehicle,
                "near_field_imminent": near_field_imminent,
                "box_width_ratio": round(box_width_ratio, 4),
                "bbox_area_ratio": round(bbox_area_ratio, 4),
                "emergency_near_field": emergency_near_field,
                "relative_lateral_velocity": round(relative_lateral, 4),
                "relative_lateral_displacement": round(relative_displacement, 4),
                "vertical_displacement": round(vertical_displacement, 4),
                "trajectory_lateral": round(trajectory_lateral, 4),
                "global_lateral_velocity": round(global_lateral_velocity, 4),
                "projected_x_norm": round(projected_x_norm, 4),
                "path_conflict": path_conflict,
            }
            enriched.append(item)

            if not track["confirmed"]:
                continue
            evidence = {
                "hits": track["hits"],
                "object_label": track["label"],
                "bbox": [round(float(v), 1) for v in track["bbox"]],
                "in_ego_lane": in_ego_lane,
                "on_drivable": on_drivable,
                "expansion_rate": track["expansion_rate"],
                "lane_quality": lane["quality"],
                "near_field_threat": near_field_vehicle,
                "near_field_imminent": near_field_imminent,
                "box_width_ratio": round(box_width_ratio, 4),
                "bbox_area_ratio": round(bbox_area_ratio, 4),
                "emergency_near_field": emergency_near_field,
                "relative_lateral_velocity": round(relative_lateral, 4),
                "relative_lateral_displacement": round(relative_displacement, 4),
                "vertical_displacement": round(vertical_displacement, 4),
                "trajectory_lateral": round(trajectory_lateral, 4),
                "global_lateral_velocity": round(global_lateral_velocity, 4),
                "projected_x_norm": round(projected_x_norm, 4),
                "path_conflict": path_conflict,
                "movement_direction": movement_direction,
                "origin_side": origin_side,
                "method": "image-space risk; không phải TTC theo mét",
                "kinematics_space": "image_space",
                "relative_scale_px": track.get("relative_scale_px"),
                "relative_closing_rate_per_s": track.get(
                    "relative_closing_rate_per_s"
                ),
                "relative_closing_acceleration_per_s2": track.get(
                    "relative_closing_acceleration_per_s2"
                ),
                "relative_ttc_proxy_seconds": track.get(
                    "relative_ttc_proxy_seconds"
                ),
                "relative_kinematics_role": "advisory_image_space_only",
            }
            if track.get("metric_ttc_available"):
                evidence.update(
                    {
                        "distance_m": track.get("distance_m"),
                        "closing_speed_mps": track.get("closing_speed_mps"),
                        "ttc_seconds": track.get("ttc_seconds"),
                        "metric_ttc_confidence": track.get("metric_ttc_confidence"),
                        "metric_ttc_role": "telemetry_only; chưa dùng để kích hoạt cảnh báo",
                    }
                )
            label_vi = VI_LABELS.get(track["label"], track["label"])
            critical_now = (
                emergency_near_field
                or (
                risk >= float(self.config["fcw_critical"])
                and track["confidence"] >= float(self.config["critical_confidence_min"])
                and near_field_imminent
                and (path_conflict or emergency_near_field)
                and proximity >= float(self.config.get("critical_proximity_min", 0.65))
                and approach >= float(self.config.get("critical_approach_min", 0.18))
                and float(track["age_seconds"]) >= 0.75
                )
            )
            allow_fcw = self._fcw_armed[track_id] or (
                critical_now and self._fcw_last_severity.get(track_id) != "critical"
            )
            if (
                track["label"] in {"car", "bus", "truck", "motorcycle", "bicycle", "rider"}
                and (path_conflict or emergency_near_field)
                and (
                    on_drivable
                    or lane_reliable
                    or near_field_vehicle
                )
                and proximity >= 0.12
                and (
                    box_width_ratio
                    >= float(self.config.get("fcw_width_ratio_min", 0.18))
                    or emergency_near_field
                )
                and (
                    float(track.get("relative_closing_rate_per_s", 0.0))
                    >= float(self.config.get("fcw_relative_rate_min", 0.20))
                    or emergency_near_field
                )
                and float(track["age_seconds"]) >= 0.40
                and risk >= float(self.config["fcw_warning"])
                and allow_fcw
                and self._confirmed_signal(
                    track_id,
                    "fcw",
                    True,
                    int(self.config.get("critical_confirmation_frames", 2))
                    if critical_now
                    else int(self.config.get("hazard_confirmation_frames", 3)),
                )
            ):
                severity = "critical" if critical_now else "warning"
                candidates.append(
                    self._candidate(
                        "fcw",
                        severity,
                        "Cảnh báo va chạm phía trước!"
                        if emergency_near_field
                        else f"{label_vi} {location}, đang tiến gần. Hãy chú ý.",
                        item,
                        {
                            **evidence,
                            "confirmation_frames_required": int(
                                self.config.get("critical_confirmation_frames", 2)
                                if critical_now
                                else self.config.get("hazard_confirmation_frames", 3)
                            ),
                            "single_frame_trigger": False,
                            "trigger_path": (
                                "image_space_emergency_override"
                                if emergency_near_field
                                else "relative_scale_fcw"
                            ),
                        },
                    )
                )
                self._fcw_armed[track_id] = False
                self._fcw_last_severity[track_id] = severity
                if severity == "critical":
                    self._critical_fcw_tracks.add(track_id)

            if (
                track["label"] in {"car", "bus", "truck"}
                and path_conflict
                and float(track["age_seconds"]) >= 0.40
            ):
                brake_score = (
                    self._brake_light_score(frame, track["bbox"])
                    if frame is not None
                    and bool(self.config.get("enable_brake_light_heuristic", False))
                    else 0.0
                )
                relative_rate = float(track.get("relative_closing_rate_per_s", 0.0))
                relative_acceleration = float(
                    track.get("relative_closing_acceleration_per_s2", 0.0)
                )
                kinematic_brake_cue = (
                    int(track.get("relative_kinematics_observations", 0)) >= 4
                    and box_width_ratio
                    >= float(self.config.get("lead_braking_width_ratio_min", 0.205))
                    and relative_rate
                    >= float(self.config.get("lead_braking_relative_rate_min", 0.10))
                    and relative_acceleration
                    >= float(
                        self.config.get("lead_braking_relative_acceleration_min", 0.12)
                    )
                )
                lamp_cue = brake_score >= float(
                    self.config.get("brake_light_score_min", 0.42)
                ) and box_width_ratio >= float(
                    self.config.get("lead_braking_lamp_width_ratio_min", 0.12)
                )
                if lamp_cue or kinematic_brake_cue:
                    self._braking_streak[int(track["track_id"])] += 1
                else:
                    self._braking_streak[int(track["track_id"])] = max(
                        0, self._braking_streak[int(track["track_id"])] - 1
                    )
                if self._braking_streak[int(track["track_id"])] >= int(
                    self.config.get("lead_braking_confirmation_frames", 3)
                ):
                    braking_evidence = {
                        **evidence,
                        "brake_light_score": round(brake_score, 4),
                        "paired_brake_lamp_cue": lamp_cue,
                        "relative_kinematic_brake_cue": kinematic_brake_cue,
                        "confirmation_frames": self._braking_streak[
                            int(track["track_id"])
                        ],
                        "lead_braking_method": (
                            "paired_lamp_plus_relative_image_space"
                            if lamp_cue and kinematic_brake_cue
                            else "paired_lamp_image_space"
                            if lamp_cue
                            else "relative_scale_acceleration_image_space"
                        ),
                        "absolute_speed_available": False,
                        "single_frame_trigger": False,
                    }
                    candidates.append(
                        self._candidate(
                            "lead_vehicle_braking",
                            "warning",
                            f"{label_vi} phía trước đang giảm tốc. Hãy chú ý.",
                            item,
                            braking_evidence,
                        )
                    )
            vulnerable_fallback = (
                not lane_reliable
                and broad_road_zone
                and proximity
                >= float(self.config.get("vulnerable_near_field_proximity", 0.18))
                and (
                    0.28 <= x_norm <= 0.72
                    or abs(relative_lateral)
                    >= float(self.config.get("vulnerable_lateral_override", 0.05))
                )
            )
            if (
                track["label"] in {"person", "rider", "motorcycle", "bicycle"}
                and (
                    on_drivable
                    or in_ego_lane
                    or vulnerable_fallback
                )
                and proximity >= 0.10
                and float(track["age_seconds"]) >= 0.40
                and path_conflict
                and (
                    risk >= float(self.config["vulnerable_warning"])
                    or vulnerable_fallback
                )
                and self._confirmed_signal(
                    track_id,
                    "vulnerable_road_user",
                    True,
                    int(self.config.get("hazard_confirmation_frames", 3)),
                )
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

            moving_toward_center = (x_norm < 0.5 and trajectory_lateral > 0.018) or (
                x_norm > 0.5 and trajectory_lateral < -0.018
            )
            longitudinal_dominant = (
                vertical_displacement > 0.008
                and abs(vertical_displacement)
                >= float(self.config.get("cut_in_longitudinal_ratio", 1.25))
                * max(abs(relative_displacement), 1e-4)
            )
            cut_in_maneuver = moving_toward_center and (
                longitudinal_dominant
                or approach >= float(self.config.get("cut_in_approach_min", 0.02))
            )
            vehicle_merge_override = (
                track["label"] in {"car", "bus", "truck"}
                and cut_in_maneuver
                and path_conflict_relaxed
                and proximity >= 0.08
                and approach >= 0.02
            )
            if (
                not in_ego_lane
                and (on_drivable or not lane_reliable)
                and float(track["age_seconds"]) >= 0.50
                and cut_in_maneuver
                and corridor_left - 0.12 <= projected_x_norm <= corridor_right + 0.12
                and (
                    vehicle_merge_override
                    or risk >= float(self.config["cut_in_warning"])
                    or proximity >= float(self.config.get("cut_in_proximity_override", 0.30))
                )
                and self._confirmed_signal(
                    track_id,
                    "cut_in",
                    True,
                    int(self.config.get("trajectory_confirmation_frames", 2)),
                )
            ):
                origin_location = (
                    "phía trước bên trái"
                    if evidence["origin_side"] == "left"
                    else "phía trước bên phải"
                    if evidence["origin_side"] == "right"
                    else location
                )
                candidates.append(
                    self._candidate(
                        "cut_in",
                        "warning",
                        f"{label_vi} {origin_location} có xu hướng nhập làn.",
                        {**item, "location": origin_location},
                        evidence,
                    )
                )

            lateral_min = float(self.config.get("cross_traffic_lateral_min", 0.028))
            cross_displacement_min = float(
                self.config.get("cross_traffic_displacement_min", 0.025)
            )
            cross_vehicle_quality = (
                track["label"] not in {"car", "bus", "truck"}
                or (
                    float(track["confidence"])
                    >= float(self.config.get("cross_vehicle_confidence_min", 0.55))
                    and motion_observations
                    >= int(self.config.get("cross_vehicle_motion_observations_min", 6))
                )
            )
            cross_motion_valid = (
                cross_vehicle_quality
                and
                motion_observations
                >= int(self.config.get("cross_traffic_motion_observations_min", 5))
                and abs(relative_displacement) >= cross_displacement_min
                and abs(relative_lateral) >= lateral_min
                and abs(relative_displacement)
                >= float(self.config.get("cross_traffic_lateral_dominance_ratio", 0.65))
                * max(abs(vertical_displacement), 1e-4)
                and float(track.get("relative_closing_rate_per_s", 0.0))
                >= float(self.config.get("cross_traffic_relative_rate_min", -0.15))
                and (
                    (origin_side == "left" and relative_displacement > 0.0)
                    or (origin_side == "right" and relative_displacement < 0.0)
                    or origin_side == "front"
                )
            )
            if (
                track["label"]
                in {"person", "rider", "motorcycle", "bicycle", "car", "bus", "truck"}
                and (on_drivable or not lane_reliable)
                and not in_ego_lane
                and cross_motion_valid
                and not cut_in_maneuver
                and not near_field_imminent
                and track_id not in self._critical_fcw_tracks
                and corridor_left - 0.12 <= projected_x_norm <= corridor_right + 0.12
                and proximity >= 0.08
                and float(track["age_seconds"]) >= 0.40
                and self._confirmed_signal(
                    track_id,
                    "cross_traffic",
                    True,
                    int(self.config.get("trajectory_confirmation_frames", 2)),
                )
            ):
                direction_vi = (
                    "từ trái sang phải"
                    if movement_direction == "left_to_right"
                    else "từ phải sang trái"
                )
                candidates.append(
                    self._candidate(
                        "cross_traffic",
                        "warning",
                        f"{label_vi} đang cắt ngang {direction_vi} phía trước. Hãy chú ý.",
                        item,
                        {
                            **evidence,
                            "lateral_velocity": relative_lateral,
                            "motion_observations": motion_observations,
                            "cross_motion_valid": cross_motion_valid,
                            "cross_vehicle_quality": cross_vehicle_quality,
                            "static_object_suppression": "passed_multi_frame_displacement_gate",
                        },
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
            now = time.monotonic() if timestamp is None else float(timestamp)
            visible_ids: set[int] = set()
            best_by_class: dict[int, tuple[dict[str, Any], Any, float]] = {}
            trace: list[dict[str, Any]] = []
            for sign in signs:
                class_id = int(sign["class_id"])
                policy = policy_for_label(str(sign["label"]))
                visual_score = self._speed_sign_visual_score(frame, sign["bbox"])
                geometry_ok = self._valid_traffic_sign_geometry(
                    sign["bbox"],
                    frame_shape,
                    speed=bool(policy and policy.require_red_ring),
                    visual_score=visual_score,
                    classifier_confidence=float(sign.get("speed_classifier_confidence", 0.0)),
                )
                reason = "eligible"
                if policy is None:
                    reason = "hud_only_unmapped"
                elif not geometry_ok:
                    reason = "geometry_gate"
                trace.append(
                    {
                        "class_id": class_id,
                        "label": sign["label"],
                        "confidence": sign["confidence"],
                        "bbox": sign["bbox"],
                        "policy": None if policy is None else policy.kind,
                        "geometry_ok": geometry_ok,
                        "visual_red_ring_score": round(visual_score, 4),
                        "decision": reason,
                    }
                )
                if policy is None or not geometry_ok:
                    continue
                previous = best_by_class.get(class_id)
                if previous is None or float(sign["confidence"]) > float(previous[0]["confidence"]):
                    best_by_class[class_id] = (sign, policy, visual_score)

            for class_id, (sign, policy, visual_score) in best_by_class.items():
                visible_ids.add(class_id)
                stable_box = (
                    class_id in self._sign_last_bbox
                    and self._traffic_sign_track_stable(
                        self._sign_last_bbox[class_id],
                        sign["bbox"],
                        frame_shape,
                    )
                )
                if not stable_box:
                    self._sign_hits[class_id] = 1
                    self._sign_first_seen[class_id] = now
                    self._sign_first_bbox[class_id] = list(sign["bbox"])
                else:
                    self._sign_hits[class_id] += 1
                self._sign_last_seen[class_id] = now
                self._sign_last_bbox[class_id] = list(sign["bbox"])
                confirmed_duration = now - self._sign_first_seen.get(class_id, now)
                sign_motion = self._bbox_motion_score(
                    self._sign_first_bbox.get(class_id, sign["bbox"]), sign["bbox"]
                )
                red_required = bool(policy.require_red_ring) and bool(
                    self.config.get("speed_sign_visual_validation", True)
                )
                red_ok = (
                    frame is None
                    or not red_required
                    or visual_score >= float(self.config.get("speed_sign_red_ring_min", 0.018))
                )
                # A moving, temporally stable high-confidence box is a safe
                # fallback for tiny/compressed signs whose red border loses
                # saturation. This replaces the old hard motion gate, which
                # rejected real signs that stayed nearly stationary.
                compressed_sign_fallback = (
                    float(sign["confidence"])
                    >= float(self.config.get("speed_sign_fallback_confidence", 0.72))
                    and sign_motion >= float(self.config.get("speed_sign_fallback_motion_min", 0.035))
                )
                visual_ok = red_ok or compressed_sign_fallback
                hits_required = int(
                    self.config.get(
                        "speed_sign_confirmation_hits" if policy.require_red_ring else "traffic_sign_confirmation_hits",
                        3,
                    )
                )
                seconds_required = float(
                    self.config.get(
                        "speed_sign_confirmation_seconds" if policy.require_red_ring else "traffic_sign_confirmation_seconds",
                        0.25,
                    )
                )
                confirmed = (
                    self._sign_hits[class_id] >= hits_required
                    and confirmed_duration >= seconds_required
                    and visual_ok
                )
                for item in trace:
                    if item["class_id"] == class_id and item["bbox"] == sign["bbox"]:
                        item.update(
                            {
                                "hits": self._sign_hits[class_id],
                                "confirmation_seconds": round(confirmed_duration, 3),
                                "screen_motion_score": round(sign_motion, 4),
                                "visual_ok": visual_ok,
                                "decision": "confirmed" if confirmed else "temporal_or_visual_gate",
                            }
                        )
                if confirmed:
                    speed = speed_value(str(sign["label"]))
                    event_type = "speed_sign" if speed is not None else "traffic_sign"
                    candidates.append(
                        {
                            "event_type": event_type,
                            "severity": policy.severity,
                            "message": policy.message,
                            "confidence": sign["confidence"],
                            "risk_score": policy.risk_score,
                            "object_id": None,
                            "location": "phía trước",
                            "cooldown_key": (
                                f"speed_sign:{speed}"
                                if speed is not None
                                else f"traffic_sign:{class_id}"
                            ),
                            "is_traffic_sign": True,
                            "audio_eligible": policy.audio_eligible,
                            "evidence": {
                                "class_id": class_id,
                                "speed_value": speed,
                                "sign_kind": policy.kind,
                                "label": sign["label"],
                                "hits": self._sign_hits[class_id],
                                "bbox": sign["bbox"],
                                "visual_red_ring_score": round(visual_score, 4),
                                "confirmation_seconds": round(confirmed_duration, 3),
                                "screen_motion_score": round(sign_motion, 4),
                                "state": "confirmed",
                            },
                        }
                    )
            self.last_sign_trace = trace[-20:]
            for class_id in list(self._sign_hits):
                if class_id not in visible_ids and now - self._sign_last_seen[class_id] > 2.0:
                    self._sign_hits[class_id] = 0

        return candidates, enriched, lane

    def _valid_speed_sign_geometry(
        self,
        bbox: list[float],
        frame_shape: tuple[int, int],
        visual_score: float = 0.0,
        classifier_confidence: float = 0.0,
    ) -> bool:
        height, width = frame_shape
        x1, y1, x2, y2 = bbox
        box_width = max(0.0, x2 - x1)
        box_height = max(0.0, y2 - y1)
        area_ratio = box_width * box_height / max(width * height, 1)
        aspect = box_width / max(box_height, 1e-6)
        regular_area = area_ratio <= float(self.config.get("speed_sign_max_area_ratio", 0.025))
        close_sign_evidence = (
            area_ratio <= float(self.config.get("speed_sign_close_max_area_ratio", 0.06))
            and visual_score >= float(self.config.get("speed_sign_close_red_ring_min", 0.08))
            and classifier_confidence
            >= float(self.config.get("speed_sign_close_classifier_confidence_min", 0.90))
        )
        return (
            float(self.config.get("speed_sign_min_area_ratio", 0.00008)) <= area_ratio
            and (regular_area or close_sign_evidence)
            and float(self.config.get("speed_sign_aspect_min", 0.55)) <= aspect
            <= float(self.config.get("speed_sign_aspect_max", 1.55))
            and y2 <= height * float(self.config.get("speed_sign_max_bottom_ratio", 0.82))
        )

    def _traffic_sign_track_stable(
        self,
        previous: list[float],
        current: list[float],
        frame_shape: tuple[int, int],
    ) -> bool:
        if bbox_iou(previous, current) >= float(
            self.config.get("traffic_sign_tracking_iou_min", 0.25)
        ):
            return True
        height, width = frame_shape
        previous_center = (
            (previous[0] + previous[2]) * 0.5,
            (previous[1] + previous[3]) * 0.5,
        )
        current_center = (
            (current[0] + current[2]) * 0.5,
            (current[1] + current[3]) * 0.5,
        )
        center_distance = math.hypot(
            current_center[0] - previous_center[0],
            current_center[1] - previous_center[1],
        ) / max(math.hypot(width, height), 1.0)
        previous_area = max(
            (previous[2] - previous[0]) * (previous[3] - previous[1]), 1.0
        )
        current_area = max(
            (current[2] - current[0]) * (current[3] - current[1]), 1.0
        )
        scale_ratio = math.sqrt(min(previous_area, current_area) / max(previous_area, current_area))
        return (
            center_distance
            <= float(self.config.get("traffic_sign_tracking_center_distance_max", 0.055))
            and scale_ratio
            >= float(self.config.get("traffic_sign_tracking_scale_ratio_min", 0.45))
        )

    def _valid_traffic_sign_geometry(
        self,
        bbox: list[float],
        frame_shape: tuple[int, int],
        speed: bool = False,
        visual_score: float = 0.0,
        classifier_confidence: float = 0.0,
    ) -> bool:
        if speed:
            return self._valid_speed_sign_geometry(
                bbox,
                frame_shape,
                visual_score=visual_score,
                classifier_confidence=classifier_confidence,
            )
        height, width = frame_shape
        x1, y1, x2, y2 = bbox
        box_width = max(0.0, x2 - x1)
        box_height = max(0.0, y2 - y1)
        area_ratio = box_width * box_height / max(width * height, 1)
        aspect = box_width / max(box_height, 1e-6)
        return (
            float(self.config.get("traffic_sign_min_area_ratio", 0.00006)) <= area_ratio
            <= float(self.config.get("traffic_sign_max_area_ratio", 0.06))
            and float(self.config.get("traffic_sign_aspect_min", 0.32)) <= aspect
            <= float(self.config.get("traffic_sign_aspect_max", 2.4))
            and y2 <= height * float(self.config.get("traffic_sign_max_bottom_ratio", 0.90))
        )

    @staticmethod
    def _speed_sign_visual_score(frame: np.ndarray | None, bbox: list[float]) -> float:
        """Estimate red-border evidence used by Vietnamese circular speed signs."""
        if frame is None:
            return 1.0
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = [int(round(value)) for value in bbox]
        pad_x = max(2, int((x2 - x1) * 0.08))
        pad_y = max(2, int((y2 - y1) * 0.08))
        x1, x2 = max(0, x1 - pad_x), min(width, x2 + pad_x)
        y1, y2 = max(0, y1 - pad_y), min(height, y2 + pad_y)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0 or min(roi.shape[:2]) < 8:
            return 0.0
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        red = ((hsv[:, :, 0] <= 10) | (hsv[:, :, 0] >= 170)) & (
            hsv[:, :, 1] >= 70
        ) & (hsv[:, :, 2] >= 60)
        roi_h, roi_w = red.shape
        yy, xx = np.ogrid[:roi_h, :roi_w]
        nx = (xx - (roi_w - 1) / 2) / max(roi_w / 2, 1)
        ny = (yy - (roi_h - 1) / 2) / max(roi_h / 2, 1)
        radius = np.sqrt(nx * nx + ny * ny)
        ring = (radius >= 0.55) & (radius <= 1.05)
        return float(red[ring].mean()) if np.any(ring) else 0.0

    @staticmethod
    def _bbox_motion_score(first: list[float], current: list[float]) -> float:
        first_width = max(first[2] - first[0], 1.0)
        first_height = max(first[3] - first[1], 1.0)
        first_cx = (first[0] + first[2]) * 0.5
        first_cy = (first[1] + first[3]) * 0.5
        current_cx = (current[0] + current[2]) * 0.5
        current_cy = (current[1] + current[3]) * 0.5
        displacement = math.hypot(
            (current_cx - first_cx) / first_width,
            (current_cy - first_cy) / first_height,
        )
        first_area = first_width * first_height
        current_area = max((current[2] - current[0]) * (current[3] - current[1]), 1.0)
        scale_change = abs(math.log(current_area / first_area))
        return float(displacement + scale_change)

    @staticmethod
    def _brake_light_score(frame: np.ndarray, bbox: list[float]) -> float:
        """Conservative paired-red-lamp cue; experimental, not a braking ground truth."""
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, x2 = max(0, x1), min(width, x2)
        y1, y2 = max(0, y1), min(height, y2)
        if x2 - x1 < 24 or y2 - y1 < 18:
            return 0.0
        roi = frame[y1 + int((y2 - y1) * 0.35): y1 + int((y2 - y1) * 0.82), x1:x2]
        if roi.size == 0:
            return 0.0
        blue, green, red = [roi[:, :, index].astype(np.float32) for index in range(3)]
        red_mask = (red > 150) & (red > green * 1.35) & (red > blue * 1.25)
        midpoint = red_mask.shape[1] // 2
        if midpoint < 1:
            return 0.0
        left_ratio = float(red_mask[:, :midpoint].mean())
        right_ratio = float(red_mask[:, midpoint:].mean())
        paired = min(left_ratio, right_ratio)
        coverage = float(red_mask.mean())
        return _clamp(paired * 18.0 + coverage * 4.0)

    def _confirmed_signal(
        self, track_id: int, event_type: str, condition: bool, required_frames: int
    ) -> bool:
        key = (track_id, event_type)
        if not condition:
            self._signal_streak[key] = 0
            self._signal_last_frame.pop(key, None)
            return False
        if self._signal_last_frame.get(key) != self._analysis_frame - 1:
            self._signal_streak[key] = 0
        self._signal_streak[key] += 1
        self._signal_last_frame[key] = self._analysis_frame
        return self._signal_streak[key] >= max(1, required_frames)

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
            "event_priority": (
                5
                if event_type == "cut_in" and str(track["label"]) in {"car", "bus", "truck"}
                else 5
                if event_type == "cross_traffic"
                and str(track["label"]) in {"person", "rider", "motorcycle", "bicycle"}
                else {
                    "fcw": 0,
                    "vulnerable_road_user": 1,
                    "cut_in": 2,
                    "lead_vehicle_braking": 3,
                    "cross_traffic": 4,
                }.get(event_type, 0)
            ),
            # Track IDs fragment under occlusion and scene cuts. Hazard-region
            # cooldown prevents the same physical threat being announced again
            # merely because the tracker assigned a new ID.
            "cooldown_key": (
                f"{event_type}:{semantic_family(str(track['label']))}:{track['location']}"
            ),
            "evidence": evidence,
        }


def moving_toward_center_hint(x_norm: float, lateral_velocity: float) -> bool:
    return (x_norm < 0.5 and lateral_velocity > 0.018) or (
        x_norm > 0.5 and lateral_velocity < -0.018
    )
