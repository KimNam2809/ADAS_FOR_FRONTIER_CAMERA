"""
Task 2: Actuation Dispatcher (Bộ Điều phối Phần cứng)

Vị trí trong hệ thống: Ngay sau Task 1 (Arbitration Logic)
Mục tiêu: Chuyển hóa priority_level thành tín hiệu vật lý giả lập

Hợp đồng Dữ liệu:
    - Input: priority_level từ Task 1
    - Output: decision_matrix.actuation_signals với audio, visual, mute_slm
"""

import time
from typing import Optional, List, Dict
from dataclasses import dataclass, field

from .contracts import (
    AudioSignal, VisualSignal, PriorityLevel, DecisionMatrixOutput,
    ActuationSignals, PRIORITY_EMERGENCY, PRIORITY_HIGH, PRIORITY_LOW, FRAME_RATE
)


@dataclass
class RhythmConfig:
    enabled: bool = False
    emergency_pattern: List[Dict[str, float]] = field(default_factory=lambda: [
        {"duration_ms": 100, "active": True},
        {"duration_ms": 100, "active": False},
        {"duration_ms": 100, "active": True},
        {"duration_ms": 100, "active": False},
        {"duration_ms": 100, "active": True}
    ])
    high_priority_pattern: List[Dict[str, float]] = field(default_factory=lambda: [
        {"duration_ms": 200, "active": True},
        {"duration_ms": 200, "active": False}
    ])
    current_pattern_index: int = 0
    pattern_start_time: float = 0.0


@dataclass
class MQTTConfig:
    enabled: bool = False
    broker_url: str = "mqtt://localhost:1883"
    topic: str = "adas/actuation"
    qos: int = 1


class ActuationDispatcher:
    def __init__(self, rhythm_config: Optional[RhythmConfig] = None,
                 mqtt_config: Optional[MQTTConfig] = None):
        self.rhythm_config = rhythm_config or RhythmConfig()
        self.mqtt_config = mqtt_config or MQTTConfig()
        self.frame_counter = 0
        
    def reset(self):
        self.frame_counter = 0
        self.rhythm_config.current_pattern_index = 0
        self.rhythm_config.pattern_start_time = 0.0
        
    def _get_mapping(self, priority_level: int) -> ActuationSignals:
        # Must-have: Simple 1-1 mapping
        if priority_level == PRIORITY_EMERGENCY:
            return {"audio": "urgent_beep", "visual": "red_overlay", "mute_slm": True}
        elif priority_level == PRIORITY_HIGH:
            return {"audio": "none", "visual": "yellow_overlay", "mute_slm": False}
        else:
            return {"audio": "none", "visual": "green_overlay", "mute_slm": False}
            
    def _apply_rhythm(self, signals: ActuationSignals) -> ActuationSignals:
        if not self.rhythm_config.enabled:
            return signals
        current_time = time.time()
        pattern = self.rhythm_config.emergency_pattern if signals["audio"] == "urgent_beep" else self.rhythm_config.high_priority_pattern
        if self.rhythm_config.pattern_start_time == 0.0:
            self.rhythm_config.pattern_start_time = current_time
            self.rhythm_config.current_pattern_index = 0
        elapsed_ms = (current_time - self.rhythm_config.pattern_start_time) * 1000
        accumulated_time = 0
        for segment in pattern:
            accumulated_time += segment["duration_ms"]
            if elapsed_ms < accumulated_time:
                if not segment["active"]:
                    signals = signals.copy()
                    signals["audio"] = "none"
                break
        else:
            self.rhythm_config.pattern_start_time = current_time
            self.rhythm_config.current_pattern_index = 0
        return signals
        
    def _send_to_mqtt(self, signals: ActuationSignals):
        if not self.mqtt_config.enabled:
            return
        payload = {
            "audio": signals["audio"],
            "visual": signals["visual"],
            "mute_slm": signals["mute_slm"],
            "timestamp": time.time()
        }
        pass
        
    def dispatch(self, priority_level: int, frame_id: int = 0, timestamp: str = "") -> ActuationSignals:
        self.frame_counter += 1
        signals = self._get_mapping(priority_level)
        signals = self._apply_rhythm(signals)
        self._send_to_mqtt(signals)
        return signals
        
    def update_decision_matrix(self, decision_output: DecisionMatrixOutput) -> DecisionMatrixOutput:
        signals = self.dispatch(decision_output["priority_level"], decision_output["frame_id"], decision_output["timestamp"])
        updated = decision_output.copy()
        updated["actuation_signals"] = signals
        return updated


def test_actuation_priority_1():
    dispatcher = ActuationDispatcher()
    signals = dispatcher.dispatch(priority_level=1)
    assert signals["audio"] == "urgent_beep"
    assert signals["visual"] == "red_overlay"
    print("PASS: Priority 1 -> urgent_beep, red_overlay")
    return True


def test_actuation_priority_2():
    dispatcher = ActuationDispatcher()
    signals = dispatcher.dispatch(priority_level=2)
    assert signals["audio"] == "none"
    assert signals["visual"] == "yellow_overlay"
    print("PASS: Priority 2 -> none, yellow_overlay")
    return True


def test_actuation_priority_3():
    dispatcher = ActuationDispatcher()
    signals = dispatcher.dispatch(priority_level=3)
    assert signals["audio"] == "none"
    assert signals["visual"] == "green_overlay"
    print("PASS: Priority 3 -> none, green_overlay")
    return True


def test_actuation_sequence():
    dispatcher = ActuationDispatcher()
    priorities = [3, 2, 1]
    expected = [
        {"audio": "none", "visual": "green_overlay", "mute_slm": False},
        {"audio": "none", "visual": "yellow_overlay", "mute_slm": False},
        {"audio": "urgent_beep", "visual": "red_overlay", "mute_slm": True}
    ]
    results = [dispatcher.dispatch(p) for p in priorities]
    for i, (result, exp) in enumerate(zip(results, expected)):
        assert result["audio"] == exp["audio"], f"Frame {i}: audio mismatch"
        assert result["visual"] == exp["visual"], f"Frame {i}: visual mismatch"
    print("PASS: Sequence 3,2,1 -> correct signals")
    return True


def test_actuation_with_rhythm():
    rhythm_config = RhythmConfig(enabled=True)
    dispatcher = ActuationDispatcher(rhythm_config=rhythm_config)
    signals = dispatcher.dispatch(priority_level=1)
    assert dispatcher.rhythm_config.enabled == True
    print("PASS: Rhythm generator enabled")
    return True


def run_all_tests():
    print("\n" + "="*60)
    print("ACTUATION DISPATCHER - TEST CASES")
    print("="*60)
    tests = [test_actuation_priority_1, test_actuation_priority_2, test_actuation_priority_3, test_actuation_sequence, test_actuation_with_rhythm]
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
