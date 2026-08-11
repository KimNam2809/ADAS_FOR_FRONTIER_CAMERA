"""
Task 3: MuteSLM Logic (Cơ chế Ngắt/Khóa Audio)

Vị trí trong hệ thống: Chốt chặn cuối cùng của khối actuation_signals
Mục tiêu: Giải bài toán tranh chấp tài nguyên âm thanh

Hợp đồng Dữ liệu:
    - Input: priority_level
    - Output: mute_slm (boolean) trong actuation_signals
"""

from typing import Optional
from dataclasses import dataclass

from .contracts import (
    DecisionMatrixOutput, ActuationSignals,
    PRIORITY_EMERGENCY, PRIORITY_HIGH, PRIORITY_LOW, COOLDOWN_FRAMES
)


@dataclass
class CooldownConfig:
    enabled: bool = True
    duration_frames: int = COOLDOWN_FRAMES
    remaining_frames: int = 0


class MuteSLMLogic:
    def __init__(self, cooldown_config: Optional[CooldownConfig] = None):
        self.cooldown_config = cooldown_config or CooldownConfig()
        self.frame_counter = 0
        self._was_critical = False
        self._cooldown_active = False
        
    def reset(self):
        self.frame_counter = 0
        self._was_critical = False
        self._cooldown_active = False
        self.cooldown_config.remaining_frames = 0
        
    def _check_critical_priority(self, priority_level: int) -> bool:
        return priority_level == PRIORITY_EMERGENCY
        
    def _apply_cooldown(self) -> bool:
        if not self.cooldown_config.enabled:
            return False
        if self._cooldown_active:
            self.cooldown_config.remaining_frames -= 1
            if self.cooldown_config.remaining_frames <= 0:
                self._cooldown_active = False
            else:
                return True
        return False
        
    def _trigger_cooldown(self):
        if self.cooldown_config.enabled:
            self._cooldown_active = True
            self.cooldown_config.remaining_frames = self.cooldown_config.duration_frames
            
    def process(self, priority_level: int) -> bool:
        self.frame_counter += 1
        is_critical = self._check_critical_priority(priority_level)
        in_cooldown = self._apply_cooldown()
        mute_slm = is_critical or in_cooldown
        if is_critical:
            self._was_critical = True
        elif self._was_critical and not is_critical:
            self._trigger_cooldown()
            self._was_critical = False
            mute_slm = True
        return mute_slm
        
    def update_actuation_signals(self, decision_output: DecisionMatrixOutput) -> DecisionMatrixOutput:
        mute_slm = self.process(decision_output["priority_level"])
        updated = decision_output.copy()
        updated["actuation_signals"] = decision_output["actuation_signals"].copy()
        updated["actuation_signals"]["mute_slm"] = mute_slm
        return updated


def test_mute_slm_priority_1():
    mute_logic = MuteSLMLogic()
    assert mute_logic.process(priority_level=1) == True
    print("PASS: Priority 1 always mutes SLM")
    return True


def test_mute_slm_priority_2_3():
    mute_logic = MuteSLMLogic()
    mute_logic.cooldown_config.enabled = False
    assert mute_logic.process(priority_level=2) == False
    assert mute_logic.process(priority_level=3) == False
    print("PASS: Priority 2 and 3 don't mute SLM")
    return True


def test_mute_slm_basic():
    mute_logic = MuteSLMLogic()
    for frame_id in range(121):
        assert mute_logic.process(priority_level=3) == False
    assert mute_logic.process(priority_level=1) == True
    print("PASS: Frame 121 triggers mute_slm = True")
    return True


def test_mute_slm_cooldown():
    cooldown_config = CooldownConfig(enabled=True, duration_frames=60)
    mute_logic = MuteSLMLogic(cooldown_config=cooldown_config)
    assert mute_logic.process(priority_level=1) == True
    assert mute_logic.process(priority_level=3) == True
    for frame_id in range(102, 160):
        assert mute_logic.process(priority_level=3) == True
    assert mute_logic.process(priority_level=3) == False
    print("PASS: Cooldown maintains mute for 60 frames")
    return True


def test_mute_slm_transition():
    cooldown_config = CooldownConfig(enabled=True, duration_frames=10)
    mute_logic = MuteSLMLogic(cooldown_config=cooldown_config)
    assert mute_logic.process(priority_level=1) == True
    assert mute_logic.process(priority_level=1) == True
    assert mute_logic.process(priority_level=3) == True
    for _ in range(8):
        assert mute_logic.process(priority_level=3) == True
    assert mute_logic.process(priority_level=3) == False
    print("PASS: Transition triggers cooldown correctly")
    return True


def run_all_tests():
    print("\n" + "="*60)
    print("MUTE SLM LOGIC - TEST CASES")
    print("="*60)
    tests = [test_mute_slm_priority_1, test_mute_slm_priority_2_3, test_mute_slm_basic, test_mute_slm_cooldown, test_mute_slm_transition]
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
