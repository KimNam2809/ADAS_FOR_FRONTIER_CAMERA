from itertools import permutations

from roadwatch.alerts import AlertGovernor
from roadwatch.sign_arbitration import arbitrate_sign_candidates


def config() -> dict:
    return {"alerts": {
        "global_audio_gap_seconds": 2.5,
        "warning_cooldown_seconds": 7.0,
        "critical_cooldown_seconds": 2.0,
        "sign_cooldown_seconds": 20.0,
    }}


def sign(key: str, kind: str, severity: str, risk: float) -> dict:
    speed_value = int(key.rsplit(":", 1)[1]) if key.startswith("speed_sign:") else None
    return {
        "event_type": "speed_sign" if kind == "speed_limit" else "traffic_sign",
        "severity": severity,
        "message": key,
        "risk_score": risk,
        "confidence": 0.9,
        "object_id": None,
        "location": "phía trước",
        "cooldown_key": key,
        "is_traffic_sign": True,
        "audio_eligible": True,
        "evidence": {"sign_kind": kind, "speed_value": speed_value},
    }


SIGNS = [
    sign("speed_sign:60", "speed_limit", "advisory", 0.30),
    sign("speed_sign:80", "speed_limit", "advisory", 0.32),
    sign("traffic_sign:stop", "stop", "warning", 0.76),
    sign("traffic_sign:work", "local_hazard", "warning", 0.70),
    sign("traffic_sign:parking", "information", "informational", 0.15),
]


def test_at_least_30_input_permutations_have_identical_sign_decision() -> None:
    signatures = set()
    for variant in list(permutations(SIGNS))[:60]:
        selected, suppressed = arbitrate_sign_candidates(list(variant))
        signatures.add((
            tuple(item["cooldown_key"] for item in selected),
            tuple(sorted(item["cooldown_key"] for item in suppressed)),
        ))
    assert len(signatures) == 1
    selected_keys, suppressed_keys = signatures.pop()
    assert selected_keys[0] == "traffic_sign:stop"
    assert "speed_sign:60" in suppressed_keys


def test_only_one_sign_is_spoken_and_same_speed_is_not_repeated_for_20_seconds() -> None:
    governor = AlertGovernor(config())
    events, _ = governor.decide(SIGNS, now=100.0, clock=10.0)
    assert sum(event["audio_action"] == "tts" for event in events) == 1
    assert next(event for event in events if event["audio_action"] == "tts")["cooldown_key"] == "traffic_sign:stop"

    governor.reset()
    speed = SIGNS[1]
    first, _ = governor.decide([speed], now=100.0, clock=10.0)
    repeat, _ = governor.decide([speed], now=110.0, clock=20.0)
    assert first[0]["audio_action"] == "tts"
    assert repeat == []


def test_critical_road_user_preempts_all_sign_audio() -> None:
    governor = AlertGovernor(config())
    fcw = {
        "event_type": "fcw", "severity": "critical", "message": "Phanh ngay",
        "risk_score": 0.99, "confidence": 0.95, "object_id": 7,
        "location": "phía trước", "cooldown_key": "fcw:7", "evidence": {},
    }
    events, _ = governor.decide([*SIGNS, fcw], now=100.0, clock=10.0)
    assert events[0]["event_type"] == "fcw"
    assert events[0]["audio_action"] == "beep_tts"
    assert all(event["audio_action"] == "hud" for event in events[1:])


def test_conflicting_lane_speed_signs_do_not_assert_an_unbound_limit() -> None:
    selected, suppressed = arbitrate_sign_candidates(SIGNS[:2])
    assert len(selected) == 1
    assert selected[0]["cooldown_key"] == "traffic_sign:speed_limit_lane_ambiguous"
    assert selected[0]["evidence"]["speed_values"] == [60, 80]
    assert selected[0]["evidence"]["speed_value"] is None
    assert selected[0]["message"] == "Nhiều biển giới hạn tốc độ; xem làn mình."
    assert {item["cooldown_key"] for item in suppressed} == {
        "speed_sign:60",
        "speed_sign:80",
    }


def test_lane_bound_speed_wins_when_binding_confidence_is_available() -> None:
    sixty, eighty = ({**item, "evidence": dict(item["evidence"])} for item in SIGNS[:2])
    sixty["evidence"]["speed_value"] = 60
    eighty["evidence"]["speed_value"] = 80
    eighty["evidence"]["lane_binding_confidence"] = 0.91
    eighty["evidence"]["applies_to_ego_lane"] = True
    selected, _ = arbitrate_sign_candidates([sixty, eighty])
    assert [item["cooldown_key"] for item in selected] == ["speed_sign:80"]


def test_maximum_and_minimum_speed_are_combined_only_for_ego_lane() -> None:
    maximum = sign("speed_sign:80", "speed_limit", "advisory", 0.30)
    maximum["evidence"].update({
        "speed_role": "maximum",
        "applies_to_ego_lane": True,
        "lane_binding_status": "ego_lane",
        "lane_binding_confidence": 0.93,
    })
    minimum = {
        **sign("speed_sign:minimum:60", "speed_limit_minimum", "advisory", 0.30),
        "message": "Tối thiểu 60 ki-lô-mét/giờ phía trước.",
        "cooldown_key": "speed_sign:minimum:60",
        "evidence": {
            "sign_kind": "speed_limit_minimum",
            "speed_value": 60,
            "speed_role": "minimum",
            "applies_to_ego_lane": True,
            "lane_binding_status": "ego_lane",
            "lane_binding_confidence": 0.91,
        },
    }
    selected, suppressed = arbitrate_sign_candidates([maximum, minimum])

    assert len(selected) == 1
    assert selected[0]["message"] == (
        "Giới hạn 80 ki-lô-mét/giờ và tối thiểu 60 ki-lô-mét/giờ."
    )
    assert selected[0]["evidence"]["speed_role"] == "combined"
    assert minimum in suppressed


def test_maximum_and_minimum_speed_are_not_combined_without_lane_binding() -> None:
    maximum = sign("speed_sign:80", "speed_limit", "advisory", 0.30)
    minimum = {
        **sign("speed_sign:minimum:60", "speed_limit_minimum", "advisory", 0.30),
        "message": "Tối thiểu 60 ki-lô-mét/giờ phía trước.",
        "cooldown_key": "speed_sign:minimum:60",
        "evidence": {
            "sign_kind": "speed_limit_minimum",
            "speed_value": 60,
            "speed_role": "minimum",
        },
    }
    selected, _ = arbitrate_sign_candidates([maximum, minimum])

    assert selected[0]["event_type"] == "traffic_sign"
    assert selected[0]["evidence"]["lane_binding_status"] == "unknown"
    assert selected[0]["message"] == "Nhiều biển giới hạn tốc độ; xem làn mình."
