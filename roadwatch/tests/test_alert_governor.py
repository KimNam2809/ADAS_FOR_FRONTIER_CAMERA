from roadwatch.alerts import AlertGovernor


def config() -> dict:
    return {
        "alerts": {
            "global_audio_gap_seconds": 2.5,
            "warning_cooldown_seconds": 7.0,
            "critical_cooldown_seconds": 2.0,
            "sign_cooldown_seconds": 20.0,
        }
    }


def candidate(severity: str = "warning", key: str = "fcw:1", risk: float = 0.7) -> dict:
    return {
        "event_type": "fcw",
        "severity": severity,
        "message": "Nguy cơ phía trước",
        "confidence": 0.9,
        "risk_score": risk,
        "object_id": 1,
        "location": "phía trước",
        "cooldown_key": key,
        "evidence": {"hits": 4},
    }


def test_cooldown_suppresses_repeated_alert() -> None:
    governor = AlertGovernor(config())
    first, first_suppressed = governor.decide([candidate()], now=100.0)
    repeated, repeated_suppressed = governor.decide([candidate()], now=101.0)
    assert first[0]["audio_action"] == "tts"
    assert first_suppressed == 0
    assert repeated == []
    assert repeated_suppressed == 1


def test_critical_escalation_bypasses_warning_cooldown() -> None:
    governor = AlertGovernor(config())
    governor.decide([candidate("warning", risk=0.65)], now=100.0)
    events, _ = governor.decide([candidate("critical", risk=0.9)], now=101.0)
    assert events[0]["severity"] == "critical"
    assert events[0]["audio_action"] == "beep_tts"


def test_only_highest_priority_event_receives_audio() -> None:
    governor = AlertGovernor(config())
    second = candidate("critical", "fcw:2", 0.91)
    second["object_id"] = 2
    events, _ = governor.decide(
        [candidate("warning", "fcw:1", 0.65), second],
        now=100.0,
    )
    assert events[0]["audio_action"] == "beep_tts"
    assert events[1]["audio_action"] == "hud"


def test_same_object_emits_only_most_specific_warning() -> None:
    governor = AlertGovernor(config())
    base = candidate("warning", risk=0.65)
    vulnerable = {
        **base,
        "event_type": "vulnerable_road_user",
        "cooldown_key": "vulnerable:motorcycle:left",
    }
    crossing = {
        **base,
        "event_type": "cross_traffic",
        "cooldown_key": "cross:motorcycle:left",
    }
    events, suppressed = governor.decide([vulnerable, crossing], now=100.0, clock=10.0)
    assert [event["event_type"] for event in events] == ["cross_traffic"]
    assert suppressed == 1


def test_sign_audio_retries_after_global_gap_instead_of_waiting_full_cooldown() -> None:
    governor = AlertGovernor(config())
    governor.decide([candidate()], now=100.0, clock=10.0)
    sign = {
        **candidate("advisory", "speed_sign:60", 0.3),
        "event_type": "speed_sign",
        "object_id": None,
        "is_traffic_sign": True,
        "message": "Đã nhận diện biển giới hạn tốc độ 60 ki-lô-mét một giờ.",
    }
    first, _ = governor.decide([sign], now=100.2, clock=10.2)
    assert first[0]["audio_status"] == "suppressed"

    retry, _ = governor.decide([sign], now=103.0, clock=13.0)
    assert retry[0]["audio_action"] == "tts"
    assert retry[0]["spoken_message"] == retry[0]["display_message"]


def test_first_sign_near_video_clock_zero_receives_tts() -> None:
    governor = AlertGovernor(config())
    sign = {
        **candidate("advisory", "speed_sign:50", 0.3),
        "event_type": "speed_sign",
        "object_id": None,
        "is_traffic_sign": True,
        "message": "Đã nhận diện biển giới hạn tốc độ 50 ki-lô-mét một giờ.",
    }
    events, _ = governor.decide([sign], now=100.4, clock=0.4)
    assert events[0]["audio_action"] == "tts"
    assert events[0]["audio_status"] == "queued"


def test_sign_preempted_by_fcw_is_rearmed_for_later_audio() -> None:
    governor = AlertGovernor(config())
    sign = {
        **candidate("advisory", "traffic_sign:64", 0.7),
        "event_type": "traffic_sign",
        "object_id": None,
        "is_traffic_sign": True,
        "message": "Cảnh báo biển dừng lại phía trước.",
    }
    threat = candidate("warning", "fcw:1", 0.8)
    first, _ = governor.decide([threat, sign], now=100.0, clock=10.0)
    assert first[0]["event_type"] == "fcw"
    assert first[1]["audio_action"] == "hud"

    retry, _ = governor.decide([sign], now=103.0, clock=13.0)
    assert retry[0]["audio_action"] == "tts"


def test_confirmed_speed_sign_is_spoken_after_gap_even_when_sign_left_frame() -> None:
    governor = AlertGovernor(config())
    governor.decide([candidate()], now=100.0, clock=10.0)
    sign = {
        **candidate("advisory", "speed_sign:80", 0.3),
        "event_type": "speed_sign",
        "object_id": None,
        "is_traffic_sign": True,
        "message": "Đã nhận diện biển giới hạn tốc độ 80 ki-lô-mét một giờ.",
    }
    first, _ = governor.decide([sign], now=100.7, clock=10.7)
    assert first[0]["audio_status"] == "suppressed"

    retry, _ = governor.decide([], now=103.0, clock=13.0)
    assert len(retry) == 1
    assert retry[0]["event_type"] == "speed_sign"
    assert retry[0]["audio_action"] == "tts"
    assert retry[0]["supersede_key"] == "speed_sign:80"


def test_different_traffic_signs_do_not_share_audio_supersede_key() -> None:
    governor = AlertGovernor(config())
    speed = {
        **candidate("advisory", "speed_sign:80", 0.3),
        "event_type": "speed_sign",
        "object_id": None,
        "is_traffic_sign": True,
    }
    no_entry = {
        **candidate("advisory", "traffic_sign:17", 0.48),
        "event_type": "traffic_sign",
        "object_id": None,
        "is_traffic_sign": True,
    }
    speed_event, _ = governor.decide([speed], now=100.0, clock=10.0)
    governor.reset()
    no_entry_event, _ = governor.decide([no_entry], now=101.0, clock=11.0)
    assert speed_event[0]["supersede_key"] == "speed_sign:80"
    assert no_entry_event[0]["supersede_key"] == "traffic_sign:17"


def test_semantic_audio_budget_limits_advisories_but_never_critical() -> None:
    governor = AlertGovernor(config())
    for index, clock in enumerate((10.0, 13.0, 16.0)):
        item = candidate("advisory", f"vru:{index}", 0.55)
        item["object_id"] = index
        item["semantic_audio_key"] = "vru:motorcycle:right"
        events, _ = governor.decide([item], now=100.0 + clock, clock=clock)
        assert events[0]["audio_action"] == "tts"

    fourth = candidate("advisory", "vru:4", 0.55)
    fourth["object_id"] = 4
    fourth["semantic_audio_key"] = "vru:motorcycle:right"
    events, _ = governor.decide([fourth], now=120.0, clock=20.0)
    assert events[0]["audio_action"] == "hud"
    assert events[0]["suppression_reason"] == "semantic_audio_budget"

    critical = candidate("critical", "vru:critical", 0.95)
    critical["object_id"] = 5
    critical["semantic_audio_key"] = "vru:motorcycle:right"
    events, _ = governor.decide([critical], now=121.0, clock=21.0)
    assert events[0]["audio_action"] == "beep_tts"
