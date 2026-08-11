"""
Contracts and Literals for L3 Decision Matrix Module
Defines data schemas and constants used across all L3 components

Author: Senior FullStack Developer
Date: 2026-08-11
"""

from typing import Literal, TypedDict, List, Optional
from enum import IntEnum


# TYPE DEFINITIONS

class HazardLevel(IntEnum):
    """Hazard levels from Kinematics Engine (Tầng 2)"""
    SAFE = 0
    WARNING = 1
    CRITICAL = 2
    EMERGENCY = 3


class ActiveEventLiteral(str):
    """Literal types for active events"""
    NONE = "none"
    FCW = "FCW"
    LDW = "LDW"
    CUT_IN = "Cut-in"


class AudioSignalLiteral(str):
    """Literal types for audio actuation signals"""
    NONE = "none"
    URGENT_BEEP = "urgent_beep"
    NORMAL_BEEP = "normal_beep"


class VisualSignalLiteral(str):
    """Literal types for visual actuation signals"""
    NONE = "none"
    RED_OVERLAY = "red_overlay"
    YELLOW_OVERLAY = "yellow_overlay"
    GREEN_OVERLAY = "green_overlay"


ActiveEvent = Literal["none", "FCW", "LDW", "Cut-in"]
AudioSignal = Literal["none", "urgent_beep", "normal_beep"]
VisualSignal = Literal["none", "red_overlay", "yellow_overlay", "green_overlay"]
PriorityLevel = Literal[1, 2, 3]


# INPUT DATA STRUCTURES

class KinematicsData(TypedDict):
    hazard_level: int
    ttc: float
    relative_velocity: float
    lane_deviation: float


class TrackedObject(TypedDict):
    object_id: int
    class_name: str
    position: dict
    velocity: dict
    kinematics: KinematicsData
    bbox_2d: dict


class SystemAlerts(TypedDict):
    trigger_fcw: bool
    trigger_ldw: bool
    trigger_cut_in: bool


class L2OutputFrame(TypedDict):
    frame_id: int
    timestamp: str
    system_alerts: SystemAlerts
    tracked_objects: List[TrackedObject]
    ego_vehicle: dict


# OUTPUT DATA STRUCTURES

class ActuationSignals(TypedDict):
    audio: AudioSignal
    visual: VisualSignal
    mute_slm: bool


class DecisionMatrixOutput(TypedDict):
    frame_id: int
    timestamp: str
    active_event: ActiveEvent
    priority_level: int
    actuation_signals: ActuationSignals


# CONSTANTS
FRAME_RATE = 30
FRAME_DURATION_MS = 1000 // FRAME_RATE
PRIORITY_EMERGENCY = 1
PRIORITY_HIGH = 2
PRIORITY_LOW = 3
COOLDOWN_FRAMES = 60
COOLDOWN_MS = COOLDOWN_FRAMES * FRAME_DURATION_MS
HYSTERESIS_LOCK_MS = 500
HYSTERESIS_LOCK_FRAMES = HYSTERESIS_LOCK_MS // FRAME_DURATION_MS


def get_priority_level_from_hazard(hazard_level: int) -> int:
    if hazard_level >= 3:
        return PRIORITY_EMERGENCY
    elif hazard_level >= 2:
        return PRIORITY_HIGH
    elif hazard_level >= 1:
        return PRIORITY_HIGH
    else:
        return PRIORITY_LOW
