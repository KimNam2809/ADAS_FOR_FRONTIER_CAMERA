"""
L3 Decision Matrix - Main Integration Module

Integrates all three tasks:
1. Arbitration Logic (Task 1)
2. Actuation Dispatcher (Task 2)
3. MuteSLM Logic (Task 3)

This module provides the complete Tầng 3 processing pipeline.
"""

import json
from typing import List, Optional

from .contracts import L2OutputFrame, DecisionMatrixOutput
from .arbiter import ArbitrationLogic
from .actuation_dispatcher import ActuationDispatcher
from .mute_slm import MuteSLMLogic


class L3DecisionMatrix:
    def __init__(self):
        self.arbiter = ArbitrationLogic()
        self.dispatcher = ActuationDispatcher()
        self.mute_slm = MuteSLMLogic()
        self.frame_counter = 0
        
    def reset(self):
        self.arbiter.reset()
        self.dispatcher.reset()
        self.mute_slm.reset()
        self.frame_counter = 0
        
    def process_frame(self, l2_output: L2OutputFrame) -> DecisionMatrixOutput:
        self.frame_counter += 1
        decision_output = self.arbiter.process_frame(l2_output)
        decision_output = self.dispatcher.update_decision_matrix(decision_output)
        decision_output = self.mute_slm.update_actuation_signals(decision_output)
        return decision_output
        
    def process_batch(self, frames: List[L2OutputFrame]) -> List[DecisionMatrixOutput]:
        return [self.process_frame(frame) for frame in frames]
        
    def process_file(self, input_path: str, output_path: Optional[str] = None) -> List[DecisionMatrixOutput]:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        frames = [data] if isinstance(data, dict) else data
        results = self.process_batch(frames)
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        return results


def create_mock_frame(frame_id: int, trigger_fcw: bool = False,
                      trigger_ldw: bool = False, trigger_cut_in: bool = False,
                      hazard_level: int = 0) -> L2OutputFrame:
    return {
        "frame_id": frame_id,
        "timestamp": f"2026-08-11T10:00:{frame_id//30:02d}.{frame_id%30:03d}Z",
        "system_alerts": {"trigger_fcw": trigger_fcw, "trigger_ldw": trigger_ldw, "trigger_cut_in": trigger_cut_in},
        "tracked_objects": [{
            "object_id": 1, "class_name": "car",
            "position": {"x": 100.0, "y": 50.0, "z": 25.0},
            "velocity": {"x": -5.0, "y": 0.0, "z": 0.0},
            "kinematics": {"hazard_level": hazard_level, "ttc": 0.8 if hazard_level >= 2 else 2.0, "relative_velocity": -12.5, "lane_deviation": 0.0},
            "bbox_2d": {"x_min": 300, "y_min": 200, "x_max": 400, "y_max": 300}
        }],
        "ego_vehicle": {"position": {"x": 0.0, "y": 0.0, "z": 0.0}, "velocity": {"x": 10.0, "y": 0.0, "z": 0.0}, "lane_id": 1, "lane_center_offset": -0.2}
    }


def demo_basic_scenario():
    print("\n" + "="*60)
    print("L3 DECISION MATRIX - BASIC DEMO")
    print("="*60)
    l3 = L3DecisionMatrix()
    print("\nScenario 1: FCW + LDW Conflict")
    frame1 = create_mock_frame(0, trigger_fcw=True, trigger_ldw=True, hazard_level=3)
    result1 = l3.process_frame(frame1)
    print(f"  Input: FCW=True, LDW=True")
    print(f"  Output: active_event={result1['active_event']}, priority={result1['priority_level']}")
    print(f"  Signals: {result1['actuation_signals']}")
    print("\nScenario 2: LDW Only")
    frame2 = create_mock_frame(1, trigger_ldw=True, hazard_level=2)
    result2 = l3.process_frame(frame2)
    print(f"  Input: LDW=True")
    print(f"  Output: active_event={result2['active_event']}, priority={result2['priority_level']}")
    print("\nScenario 3: No Alerts")
    frame3 = create_mock_frame(2)
    result3 = l3.process_frame(frame3)
    print(f"  Input: No alerts")
    print(f"  Output: active_event={result3['active_event']}, priority={result3['priority_level']}")
    print("="*60)


def demo_cooldown_scenario():
    print("\n" + "="*60)
    print("L3 DECISION MATRIX - COOLDOWN DEMO")
    print("="*60)
    l3 = L3DecisionMatrix()
    frames = [create_mock_frame(100, trigger_fcw=True, hazard_level=3)] + [create_mock_frame(i) for i in range(101, 161)]
    results = l3.process_batch(frames)
    print(f"\nFrame 100 (Critical): mute_slm = {results[0]['actuation_signals']['mute_slm']}")
    print(f"Frame 101 (Safe, cooldown): mute_slm = {results[1]['actuation_signals']['mute_slm']}")
    print(f"Frame 130 (Cooldown): mute_slm = {results[30]['actuation_signals']['mute_slm']}")
    print(f"Frame 160 (Cooldown ends): mute_slm = {results[60]['actuation_signals']['mute_slm']}")
    print("="*60)


if __name__ == "__main__":
    demo_basic_scenario()
    demo_cooldown_scenario()
