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
    events, _ = governor.decide(
        [candidate("warning", "fcw:1", 0.65), candidate("critical", "fcw:2", 0.91)],
        now=100.0,
    )
    assert events[0]["audio_action"] == "beep_tts"
    assert events[1]["audio_action"] == "hud"

