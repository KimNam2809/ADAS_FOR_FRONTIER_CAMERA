from __future__ import annotations

from typing import Optional

from .config import Policy
from .contracts import (
    AlertCandidate,
    KinematicsState,
    Lanes,
    TrackedObject,
)


def build_event_id(
    event_type: str,
    frame_id: int,
    track_id: Optional[int],
) -> str:
    track_part = "none" if track_id is None else str(track_id)
    return f"{event_type.lower()}_{frame_id}_{track_part}"


def evaluate_fcw(
    obj: TrackedObject,
    frame_id: int,
    policy: Policy,
) -> Optional[AlertCandidate]:
    kin: KinematicsState = obj.kinematics

    if not policy.get("fcw", "enabled", default=True):
        return None

    if not kin.is_approaching:
        return None

    if policy.get("fcw", "require_same_lane", default=True):
        if kin.lane_relation != "same_lane":
            return None

    if kin.stable_frames < policy.min_stable_frames:
        return None

    if obj.confidence < policy.min_object_confidence:
        return None

    if kin.ttc_sec is None:
        return None

    min_speed = policy.get(
        "fcw",
        "min_approaching_speed_mps",
        default=0.5,
    )

    # Quy ước: relative velocity âm = đang tiến lại gần
    if kin.relative_velocity_z_mps > -min_speed:
        return None

    critical_ttc = policy.get(
        "fcw",
        "critical_ttc_sec",
        default=1.2,
    )

    warning_ttc = policy.get(
        "fcw",
        "warning_ttc_sec",
        default=2.5,
    )

    if kin.ttc_sec <= critical_ttc:
        severity = "critical"
        priority = 1
        message_key = "slow_down_immediately"
    elif kin.ttc_sec <= warning_ttc:
        severity = "warning"
        priority = 2
        message_key = "slow_down"
    else:
        return None

    return AlertCandidate(
        event_id=build_event_id(
            "FCW",
            frame_id,
            obj.track_id,
        ),
        event_type="FCW",
        severity=severity,
        priority_level=priority,
        track_id=obj.track_id,
        message_key=message_key,
        reason={
            "ttc_sec": kin.ttc_sec,
            "relative_velocity_z_mps": (
                kin.relative_velocity_z_mps
            ),
            "lane_relation": kin.lane_relation,
            "stable_frames": kin.stable_frames,
            "object_confidence": obj.confidence,
        },
    )


def evaluate_cut_in(
    obj: TrackedObject,
    frame_id: int,
    policy: Policy,
) -> Optional[AlertCandidate]:
    kin = obj.kinematics

    if not policy.get("cut_in", "enabled", default=True):
        return None

    if not kin.is_cut_in:
        return None

    allowed_classes = policy.get(
        "cut_in",
        "allowed_classes",
        default=["motorcycle", "car", "person"],
    )

    if obj.class_name not in allowed_classes:
        return None

    min_stable_frames = policy.get(
        "cut_in",
        "min_stable_frames",
        default=5,
    )

    if kin.stable_frames < min_stable_frames:
        return None

    min_ttc = policy.get(
        "cut_in",
        "min_ttc_sec",
        default=2.5,
    )

    if kin.ttc_sec is not None and kin.ttc_sec > min_ttc:
        return None

    return AlertCandidate(
        event_id=build_event_id(
            "Cut-in",
            frame_id,
            obj.track_id,
        ),
        event_type="Cut-in",
        severity="warning",
        priority_level=2,
        track_id=obj.track_id,
        message_key=f"{obj.class_name}_cut_in_slow_down",
        reason={
            "ttc_sec": kin.ttc_sec,
            "is_cut_in": kin.is_cut_in,
            "stable_frames": kin.stable_frames,
            "lane_relation": kin.lane_relation,
        },
    )


def evaluate_ldw(
    lanes: Lanes,
    frame_id: int,
    timestamp_ms: int,
    lane_departure_started_ms: Optional[int],
    policy: Policy,
) -> tuple[
    Optional[AlertCandidate],
    Optional[int],
]:
    if not policy.get("ldw", "enabled", default=True):
        return None, None

    if not lanes.detected:
        return None, None

    probability = lanes.departure_probability

    if probability is None:
        return None, None

    threshold = policy.get(
        "ldw",
        "min_departure_probability",
        default=0.75,
    )

    persistence_ms = policy.get(
        "ldw",
        "persistence_ms",
        default=800,
    )

    if probability < threshold:
        return None, None

    if lane_departure_started_ms is None:
        lane_departure_started_ms = timestamp_ms
        return None, lane_departure_started_ms

    duration_ms = timestamp_ms - lane_departure_started_ms

    if duration_ms < persistence_ms:
        return None, lane_departure_started_ms

    candidate = AlertCandidate(
        event_id=build_event_id(
            "LDW",
            frame_id,
            None,
        ),
        event_type="LDW",
        severity="warning",
        priority_level=2,
        track_id=None,
        message_key="lane_departure",
        reason={
            "departure_probability": probability,
            "persistence_ms": duration_ms,
            "vehicle_offset_m": lanes.vehicle_offset_m,
        },
    )

    return candidate, lane_departure_started_ms