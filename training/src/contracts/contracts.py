from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================
# COMMON
# ============================================================

class FrameMetadata(BaseModel):
    frame_id: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    frame_age_ms: int = Field(default=0, ge=0)


class SceneUnderstanding(BaseModel):
    weather: Literal[
        "clear", "rainy", "foggy", "unknown"
    ] = "unknown"

    lighting: Literal[
        "day", "night", "twilight", "unknown"
    ] = "unknown"


class Lanes(BaseModel):
    detected: bool = False
    left_lane: List[List[float]] = Field(default_factory=list)
    right_lane: List[List[float]] = Field(default_factory=list)

    departure_probability: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    vehicle_offset_m: Optional[float] = None


# ============================================================
# LAYER 1
# ============================================================

ObjectClass = Literal[
    "car",
    "motorcycle",
    "person",
    "truck",
    "bus",
    "traffic_sign",
    "unknown",
]


class RawObjectDetection(BaseModel):
    class_name: ObjectClass
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: List[float]
    depth_z: Optional[float] = Field(default=None, ge=0.0)

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, value: List[float]) -> List[float]:
        if len(value) != 4:
            raise ValueError(
                "bbox must contain [x1, y1, x2, y2]"
            )

        x1, y1, x2, y2 = value

        if x2 <= x1 or y2 <= y1:
            raise ValueError(
                "bbox must satisfy x2 > x1 and y2 > y1"
            )

        return value


class Layer1_PerceptionOutput(BaseModel):
    frame_metadata: FrameMetadata
    scene_understanding: SceneUnderstanding
    objects: List[RawObjectDetection]
    lanes: Lanes


# ============================================================
# LAYER 2
# ============================================================

LaneRelation = Literal[
    "same_lane",
    "adjacent_lane",
    "outside_lane",
    "unknown",
]


class KinematicsState(BaseModel):
    # Quy ước: âm = vật thể đang tiến lại gần
    relative_velocity_z_mps: float

    ttc_sec: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    is_approaching: bool = False
    is_cut_in: bool = False
    lane_relation: LaneRelation = "unknown"

    stable_frames: int = Field(default=0, ge=0)
    occluded: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class TrackedObject(BaseModel):
    track_id: int = Field(ge=0)
    class_name: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    bbox: List[float]
    depth_z: Optional[float] = Field(default=None, ge=0.0)
    kinematics: KinematicsState


class SystemAlertFlags(BaseModel):
    trigger_fcw: bool = False
    trigger_ldw: bool = False


class Layer2_KinematicsOutput(BaseModel):
    frame_metadata: FrameMetadata
    scene_understanding: SceneUnderstanding
    tracked_objects: List[TrackedObject]
    lanes: Lanes
    system_alerts: SystemAlertFlags


# ============================================================
# LAYER 3
# ============================================================

AlertType = Literal[
    "none",
    "FCW",
    "LDW",
    "Cut-in",
    "System-Degraded",
]


Severity = Literal[
    "info",
    "warning",
    "critical",
]


class AlertCandidate(BaseModel):
    event_id: str
    event_type: AlertType
    severity: Severity
    priority_level: int = Field(ge=1, le=3)

    track_id: Optional[int] = None
    message_key: str

    reason: dict = Field(default_factory=dict)

    suppressed: bool = False
    suppression_reason: Optional[str] = None


class ActuationSignals(BaseModel):
    audio: Literal[
        "none",
        "chime",
        "urgent_beep",
    ]

    visual: Literal[
        "none",
        "yellow_overlay",
        "red_overlay",
    ]

    beep_immediate: bool = False
    tts_allowed: bool = False
    suppress_lower_priority: bool = False


class DecisionMatrix(BaseModel):
    active_event: AlertType
    active_severity: Severity
    priority_level: int = Field(ge=1, le=3)

    actuation_signals: ActuationSignals

    selected_alert: Optional[AlertCandidate] = None
    candidates: List[AlertCandidate] = Field(
        default_factory=list
    )


class PassthroughContext(BaseModel):
    scene_understanding: SceneUnderstanding
    ttc_closest_sec: Optional[float] = Field(
        default=None,
        ge=0.0,
    )
    source_frame_age_ms: int = Field(ge=0)


class Layer3_DecisionOutput(BaseModel):
    frame_metadata: FrameMetadata
    decision_matrix: DecisionMatrix
    passthrough_context: PassthroughContext