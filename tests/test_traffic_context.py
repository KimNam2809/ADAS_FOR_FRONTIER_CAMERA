from __future__ import annotations

from roadwatch.alerts import AlertGovernor
from roadwatch.signs import HUD_ONLY_DIRECTION_SIGN_LABELS, policy_for_label
from roadwatch.traffic_context import TrafficContextEngine


def _track(index: int, label: str = "motorcycle", *, sidewalk: bool = False) -> dict:
    return {
        "track_id": index,
        "class_name": label,
        "confirmed": True,
        "age_seconds": 0.8,
        "bbox": [80 + index * 20, 260, 130 + index * 20, 440],
        "on_drivable": not sidewalk,
        "in_ego_lane": not sidewalk,
        "path_conflict": False,
        "near_field_threat": False,
        "lateral_velocity": 0.0,
        "expansion_rate": 0.0,
        "relative_closing_rate_per_s": 0.0,
    }


def _governor_config() -> dict:
    return {
        "alerts": {
            "global_audio_gap_seconds": 2.5,
            "warning_cooldown_seconds": 7.0,
            "maneuver_cooldown_seconds": 15.0,
            "critical_cooldown_seconds": 2.0,
            "sign_cooldown_seconds": 20.0,
            "advisory_audio_window_seconds": 60.0,
            "advisory_audio_max_per_window": 3,
        }
    }


def _candidate(event_type: str = "cross_traffic", risk: float = 0.55) -> dict:
    return {
        "event_type": event_type,
        "severity": "warning",
        "message": "Xe máy cắt ngang bên phải.",
        "confidence": 0.9,
        "risk_score": risk,
        "object_id": 1,
        "location": "bên phải",
        "cooldown_key": f"{event_type}:1",
        "evidence": {},
    }


def test_dense_requires_stable_count_and_excludes_sidewalk_people() -> None:
    engine = TrafficContextEngine({"traffic_context": {"mode": "enforce"}})
    tracks = [_track(index) for index in range(6)] + [_track(20, "person", sidewalk=True)]
    for source_time in (0.5, 0.6):
        state = engine.update(tracks, [], (480, 640), source_time)
        assert state["mode"] == "normal"
    state = engine.update(tracks, [], (480, 640), 0.7)
    assert state["mode"] == "dense"
    assert state["confirmed_road_users"] == 6
    assert state["two_wheeler_count"] == 6
    assert state["attention_due"] is True


def test_dense_hysteresis_exits_only_after_two_seconds() -> None:
    engine = TrafficContextEngine({"traffic_context": {"mode": "enforce"}})
    tracks = [_track(index) for index in range(8)]
    for source_time in (0.5, 0.6, 0.7):
        engine.update(tracks, [], (480, 640), source_time)
    assert engine.snapshot()["mode"] == "dense"
    few = tracks[:4]
    assert engine.update(few, [], (480, 640), 1.5)["mode"] == "dense"
    assert engine.update(few, [], (480, 640), 3.6)["mode"] == "normal"


def test_context_reset_clears_entry_beep_and_history() -> None:
    engine = TrafficContextEngine({"traffic_context": {"mode": "enforce"}})
    tracks = [_track(index) for index in range(8)]
    for source_time in (0.5, 0.6, 0.7):
        engine.update(tracks, [], (480, 640), source_time)
    engine.reset()
    assert engine.snapshot()["mode"] == "normal"
    assert engine.snapshot()["attention_due"] is False


def test_context_failure_returns_normal_fallback() -> None:
    engine = TrafficContextEngine({"traffic_context": {"mode": "enforce"}})
    state = engine.update([None], [], (480, 640), 0.5)  # type: ignore[list-item]
    assert state["mode"] == "normal"
    assert state["audio_policy"] == "normal"
    assert state["fallback"] is True
    assert state["error"]


def test_dense_low_risk_is_hud_only_but_critical_stays_audio() -> None:
    governor = AlertGovernor(_governor_config())
    dense = {
        "mode": "dense",
        "policy_mode": "enforce",
        "risk_state": "calm",
    }
    low, _ = governor.decide([_candidate(risk=0.55)], now=100.0, clock=10.0, context=dense)
    assert low[0]["audio_action"] == "hud"
    assert low[0]["display_scope"] == "hud_context"
    assert low[0]["suppression_reason"] == "dense_traffic_context"

    critical_candidate = _candidate("fcw", 0.95)
    critical_candidate["severity"] = "critical"
    critical, _ = governor.decide([critical_candidate], now=101.0, clock=11.0, context={**dense, "risk_state": "threat"})
    assert critical[0]["audio_action"] == "beep_tts"
    assert critical[0]["display_scope"] == "hazard_banner"


def test_context_attention_is_one_event_without_tts() -> None:
    governor = AlertGovernor(_governor_config())
    context = {
        "mode": "dense",
        "policy_mode": "enforce",
        "risk_state": "calm",
        "attention_due": True,
        "density_score": 0.9,
        "confirmed_road_users": 8,
        "two_wheeler_count": 3,
    }
    events, _ = governor.decide([], now=100.0, clock=10.0, context=context)
    assert len(events) == 1
    assert events[0]["event_type"] == "traffic_context_attention"
    assert events[0]["audio_action"] == "context_beep"
    assert events[0]["spoken_message"] == ""
    assert events[0]["display_scope"] == "hud_context"


def test_direction_signs_are_hud_only_and_safety_sign_remains_eligible() -> None:
    for label in HUD_ONLY_DIRECTION_SIGN_LABELS:
        policy = policy_for_label(label)
        assert policy is not None
        assert policy.audio_eligible is False
    assert policy_for_label("Stop").audio_eligible is True  # type: ignore[union-attr]
