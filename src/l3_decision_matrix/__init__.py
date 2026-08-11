"""
L3 Decision Matrix Module for RoadWatch Copilot

This module implements Tầng 3 - Priority & Decision Matrix of the RoadWatch Copilot system.
It processes inputs from Tầng 2 (Kinematics Engine) and generates decision outputs for Tầng 4 (SLM).

Architecture:
    - Task 1: Arbitration Logic (Ma trận Phân luồng Ưu tiên)
    - Task 2: Actuation Dispatcher (Bộ Điều phối Phần cứng)
    - Task 3: MuteSLM Logic (Cơ chế Ngắt/Khóa Audio)

Author: Senior FullStack Developer (5 years Edge Device experience)
"""

from .contracts import (
    ActiveEvent,
    AudioSignal,
    VisualSignal,
    PriorityLevel,
    L2OutputFrame,
    DecisionMatrixOutput,
    ActuationSignals,
    SystemAlerts,
    TrackedObject,
    KinematicsData,
    PRIORITY_EMERGENCY,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    FRAME_RATE,
    COOLDOWN_FRAMES,
    HYSTERESIS_LOCK_FRAMES
)

from .arbiter import ArbitrationLogic
from .actuation_dispatcher import ActuationDispatcher
from .mute_slm import MuteSLMLogic

__version__ = "1.0.0"
__all__ = [
    "ArbitrationLogic",
    "ActuationDispatcher", 
    "MuteSLMLogic",
    "ActiveEvent",
    "AudioSignal",
    "VisualSignal",
    "PriorityLevel",
    "L2OutputFrame",
    "DecisionMatrixOutput",
    "ActuationSignals"
]