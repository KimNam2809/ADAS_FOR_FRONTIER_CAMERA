"""
Task 1: Arbitration Logic (Ma trận Phân luồng Ưu tiên)

Vị trí trong hệ thống: Entry point của Tầng 3
Mục tiêu: Xử lý xung đột tín hiệu (Signal Conflict)

Khi Tầng 2 phát hiện nhiều rủi ro cùng một lúc (Ví dụ: Xe vừa bị chệch làn LDW,
vừa sắp đâm đuôi xe trước FCW), module này chịu trách nhiệm "đè" các tín hiệu
ít nghiêm trọng hơn xuống và chỉ phát ra 1 cảnh báo sinh tử duy nhất.

Hợp đồng Dữ liệu:
    - Input: tracked_objects[].kinematics.hazard_level và system_alerts
    - Output: decision_matrix với active_event và priority_level
"""

import time
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, field

from .contracts import (
    ActiveEvent, PriorityLevel, L2OutputFrame, DecisionMatrixOutput,
    ActuationSignals, SystemAlerts, PRIORITY_EMERGENCY, PRIORITY_HIGH,
    PRIORITY_LOW, FRAME_RATE, HYSTERESIS_LOCK_FRAMES
)


class PriorityState(Enum):
    IDLE = "idle"
    LOCKED = "locked"
    COOLDOWN = "cooldown"


@dataclass
class HysteresisConfig:
    enabled: bool = True
    lock_duration_frames: int = HYSTERESIS_LOCK_FRAMES
    current_lock_frames: int = 0
    locked_priority: Optional[int] = None
    last_priority_change_time: float = 0.0


@dataclass
class PriorityRules:
    priority_order: list = field(default_factory=lambda: ["FCW", "Cut-in", "LDW"])
    hazard_thresholds: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "FCW": {"min_hazard": 1, "ttc_threshold": 1.5},
        "LDW": {"min_hazard": 2, "deviation_threshold": 0.5},
        "Cut-in": {"min_hazard": 2, "ttc_threshold": 2.0}
    })


class ArbitrationLogic:
    def __init__(self, rules: Optional[PriorityRules] = None):
        self.rules = rules or PriorityRules()
        self.hysteresis = HysteresisConfig()
        self.frame_counter = 0
        
    def reset(self):
        self.hysteresis = HysteresisConfig()
        self.frame_counter = 0
        
    def _get_highest_priority_event(self, system_alerts: SystemAlerts) -> ActiveEvent:
        # Must-have: FCW có độ ưu tiên tuyệt đối
        if system_alerts.get("trigger_fcw", False):
            return "FCW"
        if system_alerts.get("trigger_cut_in", False):
            return "Cut-in"
        if system_alerts.get("trigger_ldw", False):
            return "LDW"
        return "none"
        
    def _get_priority_level(self, event: ActiveEvent, tracked_objects: list) -> int:
        if event == "FCW":
            return PRIORITY_EMERGENCY
        elif event == "Cut-in":
            for obj in tracked_objects:
                if obj.get("kinematics", {}).get("hazard_level", 0) >= 3:
                    return PRIORITY_EMERGENCY
            return PRIORITY_HIGH
        elif event == "LDW":
            return PRIORITY_HIGH
        else:
            return PRIORITY_LOW
            
    def _apply_hysteresis(self, current_priority: int) -> int:
        if not self.hysteresis.enabled:
            return current_priority
        if self.hysteresis.locked_priority is not None:
            self.hysteresis.current_lock_frames += 1
            if self.hysteresis.current_lock_frames >= self.hysteresis.lock_duration_frames:
                self.hysteresis.locked_priority = None
                self.hysteresis.current_lock_frames = 0
            else:
                return self.hysteresis.locked_priority
        if self.hysteresis.locked_priority != current_priority:
            self.hysteresis.locked_priority = current_priority
            self.hysteresis.current_lock_frames = 0
            self.hysteresis.last_priority_change_time = time.time()
        return current_priority
        
    def process_frame(self, l2_output: L2OutputFrame) -> DecisionMatrixOutput:
        self.frame_counter += 1
        system_alerts = l2_output.get("system_alerts", {})
        tracked_objects = l2_output.get("tracked_objects", [])
        active_event = self._get_highest_priority_event(system_alerts)
        priority_level = self._get_priority_level(active_event, tracked_objects)
        priority_level = self._apply_hysteresis(priority_level)
        output: DecisionMatrixOutput = {
            "frame_id": l2_output.get("frame_id", 0),
            "timestamp": l2_output.get("timestamp", ""),
            "active_event": active_event,
            "priority_level": priority_level,
            "actuation_signals": {"audio": "none", "visual": "none", "mute_slm": False}
        }
        return output
    
    def process_batch(self, frames: list[L2OutputFrame]) -> list[DecisionMatrixOutput]:
        return [self.process_frame(frame) for frame in frames]


def test_arbiter_basic():
    arbiter = ArbitrationLogic()
    test_frame: L2OutputFrame = {
        "frame_id": 0, "timestamp": "2026-08-11T10:00:00.000Z",
        "system_alerts": {"trigger_fcw": True, "trigger_ldw": True, "trigger_cut_in": False},
        "tracked_objects": [{"object_id": 1, "kinematics": {"hazard_level": 3}}],
        "ego_vehicle": {}
    }
    result = arbiter.process_frame(test_frame)
    assert result["active_event"] == "FCW", f"Expected FCW, got {result['active_event']}"
    assert result["priority_level"] == 1, f"Expected priority 1, got {result['priority_level']}"
    print("PASS: FCW + LDW conflict -> FCW with priority 1")
    return True


def test_arbiter_ldw_only():
    arbiter = ArbitrationLogic()
    test_frame: L2OutputFrame = {
        "frame_id": 1, "timestamp": "2026-08-11T10:00:00.033Z",
        "system_alerts": {"trigger_fcw": False, "trigger_ldw": True, "trigger_cut_in": False},
        "tracked_objects": [], "ego_vehicle": {}
    }
    result = arbiter.process_frame(test_frame)
    assert result["active_event"] == "LDW"
    assert result["priority_level"] == 2
    print("PASS: LDW only -> LDW with priority 2")
    return True


def test_arbiter_cut_in():
    arbiter = ArbitrationLogic()
    test_frame: L2OutputFrame = {
        "frame_id": 2, "timestamp": "2026-08-11T10:00:00.066Z",
        "system_alerts": {"trigger_fcw": False, "trigger_ldw": False, "trigger_cut_in": True},
        "tracked_objects": [], "ego_vehicle": {}
    }
    result = arbiter.process_frame(test_frame)
    assert result["active_event"] == "Cut-in"
    print("PASS: Cut-in only -> Cut-in with priority 2")
    return True


def test_arbiter_no_alerts():
    arbiter = ArbitrationLogic()
    test_frame: L2OutputFrame = {
        "frame_id": 3, "timestamp": "2026-08-11T10:00:00.100Z",
        "system_alerts": {"trigger_fcw": False, "trigger_ldw": False, "trigger_cut_in": False},
        "tracked_objects": [], "ego_vehicle": {}
    }
    result = arbiter.process_frame(test_frame)
    assert result["active_event"] == "none"
    assert result["priority_level"] == 3
    print("PASS: No alerts -> none with priority 3")
    return True


def test_arbiter_hysteresis():
    rules = PriorityRules()
    arbiter = ArbitrationLogic(rules)
    arbiter.hysteresis.enabled = True
    arbiter.hysteresis.lock_duration_frames = 15
    frame1: L2OutputFrame = {
        "frame_id": 0, "timestamp": "",
        "system_alerts": {"trigger_fcw": True, "trigger_ldw": False, "trigger_cut_in": False},
        "tracked_objects": [], "ego_vehicle": {}
    }
    result1 = arbiter.process_frame(frame1)
    assert result1["priority_level"] == 1
    frame2: L2OutputFrame = {
        "frame_id": 1, "timestamp": "",
        "system_alerts": {"trigger_fcw": False, "trigger_ldw": True, "trigger_cut_in": False},
        "tracked_objects": [], "ego_vehicle": {}
    }
    result2 = arbiter.process_frame(frame2)
    assert result2["priority_level"] == 1
    print("PASS: Hysteresis prevents immediate priority drop")
    return True


def run_all_tests():
    print("\n" + "="*60)
    print("ARBITRATION LOGIC - TEST CASES")
    print("="*60)
    tests = [test_arbiter_basic, test_arbiter_ldw_only, test_arbiter_cut_in, test_arbiter_no_alerts, test_arbiter_hysteresis]
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
    print("="*60)
    print(f"Results: {passed}/{len(tests)} passed")
    print("="*60)
    return passed == len(tests)


if __name__ == "__main__":
    run_all_tests()
