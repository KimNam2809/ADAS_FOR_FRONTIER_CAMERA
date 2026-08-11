"""
Contracts and Literals for L3 Decision Matrix Module
Defines data schemas and constants used across all L3 components
"""

from typing import Literal, TypedDict, List, Optional
from enum import IntEnum


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

class HazardLevel(IntEnum):
    """Hazard levels from Kinematics Engine (Tầng 2)"""
    SAFE = 0
    WARNING = 1
    CRITICAL = 2
    EMERGENCY = 3


class ActiveEventLiteral(str):
    """Literal types for active events"""
    NONE = "none"
    FCW = "FCW"  # Forward Collision Warning
    LDW = "LDW"  # Lane Departure Warning
    CUT_IN = "Cut-in"  # Vehicle cutting in


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


# Type aliases for better readability
ActiveEvent = Literal["none", "FCW", "LDW", "Cut-in"]
AudioSignal = Literal["none", "urgent_beep", "normal_beep"]
VisualSignal = Literal["none", "red_overlay", "yellow_overlay", "green_overlay"]
PriorityLevel = Literal[1, 2, 3]  # 1 = highest, 3 = lowest


# =============================================================================
# INPUT DATA STRUCTURES (From Tầng 2 - Kinematics Engine)
# =============================================================================

class KinematicsData(TypedDict):
    """Kinematics data for a single tracked object"""
    hazard_level: int  # 0-3
    ttc: float  # Time-to-Collision in seconds
    relative_velocity: float  # m/s
    lane_deviation: float  # meters from lane center


class TrackedObject(TypedDict):
    """Tracked object from perception"""
    object_id: int
    class_name: str
    position: dict  # x, y, z
    velocity: dict  # x, y, z
    kinematics: KinematicsData
    bbox_2d: dict  # x_min, y_min, x_max, y_max


class SystemAlerts(TypedDict):
    """System-level alerts from Tầng 2"""
    trigger_fcw: bool
    trigger_ldw: bool
    trigger_cut_in: bool


class L2OutputFrame(TypedDict):
    """Complete input frame from Tầng 2"""
    frame_id: int
    timestamp: str
    system_alerts: SystemAlerts
    tracked_objects: List[TrackedObject]
    ego_vehicle: dict


# =============================================================================
# OUTPUT DATA STRUCTURES (To Tầng 4 - SLM)
# =============================================================================

class ActuationSignals(TypedDict):
    """Actuation signals for HMI"""
    audio: AudioSignal
    visual: VisualSignal
    mute_slm: bool  # Mute the SLM audio


class DecisionMatrixOutput(TypedDict):
    """Output structure for L3 Decision Matrix"""
    frame_id: int
    timestamp: str
    active_event: ActiveEvent
    priority_level: int  # 1, 2, or 3
    actuation_signals: ActuationSignals


# =============================================================================
# PRIORITY RULES CONFIGURATION (Nice-to-have: YAML external config)
# =============================================================================

DEFAULT_PRIORITY_RULES = {
    "priority_order": ["FCW", "Cut-in", "LDW"],  # Higher index = higher priority
    "hazard_thresholds": {
        "FCW": {"min_hazard": 1, "ttc_threshold": 1.5},
        "LDW": {"min_hazard": 2, "deviation_threshold": 0.5},
        "Cut-in": {"min_hazard": 2, "ttc_threshold": 2.0}
    },
    "hysteresis": {
        "enabled": True,
        "lock_duration_ms": 500  # Lock priority for 500ms after change
    },
    "cooldown": {
        "enabled": True,
        "duration_frames": 60  # 60 frames at 30fps = 2 seconds
    }
}


# =============================================================================
# CONSTANTS
# =============================================================================

# Frame rate assumptions
FRAME_RATE = 30  # fps
FRAME_DURATION_MS = 1000 // FRAME_RATE

# Priority level constants
PRIORITY_EMERGENCY = 1
PRIORITY_HIGH = 2
PRIORITY_LOW = 3

# Cooldown constants
COOLDOWN_FRAMES = 60  # 2 seconds at 30fps
COOLDOWN_MS = COOLDOWN_FRAMES * FRAME_DURATION_MS

# Hysteresis constants
HYSTERESIS_LOCK_MS = 500
HYSTERESIS_LOCK_FRAMES = HYSTERESIS_LOCK_MS // FRAME_DURATION_MS


def get_priority_level_from_hazard(hazard_level: int) -> int:
    """
    Map hazard level to priority level
    
    Args:
        hazard_level: 0-3 hazard level from kinematics
        
    Returns:
        priority_level: 1-3
    """
    if hazard_level >= 3:
        return PRIORITY_EMERGENCY
    elif hazard_level >= 2:
        return PRIORITY_HIGH
    elif hazard_level >= 1:
        return PRIORITY_HIGH
    else:
        return PRIORITY_LOW