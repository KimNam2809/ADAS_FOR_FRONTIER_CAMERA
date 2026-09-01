import time

import numpy as np

from roadwatch.alerts import AlertGovernor
from roadwatch.audio import AudioManager
from roadwatch.risk import RiskEngine
from roadwatch.signs import policy_for_label, resolve_sign_message


CONFIG = {
    "tracking": {"confirmation_hits": 3},
    "risk": {
        "fcw_warning": 0.56,
        "fcw_critical": 0.78,
        "vulnerable_warning": 0.52,
        "cut_in_warning": 0.60,
        "lane_quality_min": 0.48,
        "ldw_offset_warning": 0.34,
        "ldw_confirmation_frames": 5,
        "speed_sign_confirmation_hits": 3,
        "speed_sign_confirmation_seconds": 0.2,
        "speed_sign_max_area_ratio": 0.1,
        "critical_confidence_min": 0.55,
    },
    "alerts": {
        "global_audio_gap_seconds": 0.0,
        "warning_cooldown_seconds": 7.0,
        "critical_cooldown_seconds": 2.0,
        "sign_cooldown_seconds": 20.0,
        "advisory_ttl_seconds": 2.0,
        "warning_ttl_seconds": 1.5,
        "critical_ttl_seconds": 1.0,
    },
    "audio": {"enabled": True, "tts_enabled": True, "piper_voice": "missing.onnx"},
}


def empty_lane() -> dict:
    return {
        "lane_mask": np.zeros((80, 120), dtype=np.uint8),
        "drivable_mask": np.zeros((80, 120), dtype=np.uint8),
        "quality": 0.0,
    }


def sign(class_id: int, speed: int) -> dict:
    return {
        "class_id": class_id,
        "label": f"Speed limit {speed}km/h",
        "confidence": 0.9,
        "bbox": [10, 10, 30, 30],
    }


def named_sign(class_id: int, label: str) -> dict:
    return {
        "class_id": class_id,
        "label": label,
        "confidence": 0.9,
        "bbox": [10, 10, 30, 30],
    }


def test_speed_sign_state_never_reuses_previous_value() -> None:
    engine = RiskEngine(CONFIG)
    candidates = []
    for timestamp in (0.0, 0.1, 0.2):
        candidates, _, _ = engine.analyze(
            [], [sign(12, 60)], empty_lane(), (80, 120), True, timestamp=timestamp
        )
    assert candidates[0]["evidence"]["speed_value"] == 60
    assert "60" in candidates[0]["message"]

    switched, _, _ = engine.analyze(
        [], [sign(2, 40)], empty_lane(), (80, 120), True, timestamp=1.0
    )
    assert switched == []
    for timestamp in (1.1, 1.21):
        switched, _, _ = engine.analyze(
            [], [sign(2, 40)], empty_lane(), (80, 120), True, timestamp=timestamp
        )
    assert switched[0]["evidence"]["speed_value"] == 40
    assert "40" in switched[0]["message"]


def test_safety_sign_becomes_canonical_hazard_and_tts_payload() -> None:
    engine = RiskEngine(CONFIG)
    candidates = []
    for timestamp in (0.0, 0.15, 0.30):
        candidates, _, _ = engine.analyze(
            [], [named_sign(64, "Stop")], empty_lane(), (80, 120), True, timestamp=timestamp
        )
    assert candidates[0]["event_type"] == "traffic_sign"
    assert candidates[0]["severity"] == "warning"
    assert candidates[0]["is_traffic_sign"] is True
    assert candidates[0]["message"] == "Biển dừng phía trước."

    governor = AlertGovernor(CONFIG)
    events, _ = governor.decide(candidates, now=1000.0, clock=10.0)
    assert events[0]["display_message"] == events[0]["spoken_message"]
    assert events[0]["audio_action"] == "tts"


def test_low_priority_facility_sign_is_hud_only() -> None:
    engine = RiskEngine(CONFIG)
    candidates = []
    for timestamp in (0.0, 0.15, 0.30):
        candidates, _, _ = engine.analyze(
            [], [named_sign(68, "Parking")], empty_lane(), (80, 120), True, timestamp=timestamp
        )
    governor = AlertGovernor(CONFIG)
    events, _ = governor.decide(candidates, now=1000.0, clock=10.0)
    assert events[0]["audio_eligible"] is False
    assert events[0]["audio_action"] == "hud"


def test_sign_trace_explains_unmapped_raw_detection() -> None:
    engine = RiskEngine(CONFIG)
    engine.analyze(
        [], [named_sign(999, "Unknown custom sign")], empty_lane(), (80, 120), True, timestamp=0.0
    )
    assert engine.last_sign_trace[0]["decision"] == "hud_only_unmapped"


def test_governor_adds_trace_and_expiry() -> None:
    governor = AlertGovernor(CONFIG)
    candidate = {
        "event_type": "fcw",
        "severity": "warning",
        "message": "Xe phía trước",
        "confidence": 0.8,
        "risk_score": 0.7,
        "object_id": 8,
        "location": "phía trước",
        "cooldown_key": "fcw:8",
        "evidence": {},
    }
    events, _ = governor.decide(
        [candidate], now=1000.0, clock=12.0, frame_id=22, source_time=4.5
    )
    event = events[0]
    assert event["event_id"]
    assert event["frame_id"] == 22
    assert event["source_time"] == 4.5
    assert event["expires_at"] == 1001.5
    assert event["audio_status"] == "queued"
    assert event["display_message"] == event["spoken_message"] == "Xe phía trước"


def test_speed_sign_visual_gate_rejects_watermark_without_red_ring() -> None:
    frame = np.full((120, 200, 3), 220, dtype=np.uint8)
    # Yellow/black text resembles the watermark that caused the 60 km/h false positive.
    frame[15:35, 20:70] = (0, 220, 255)
    assert RiskEngine._speed_sign_visual_score(frame, [20, 15, 70, 35]) < 0.025


def test_speed_sign_visual_gate_accepts_red_circular_border() -> None:
    frame = np.full((120, 200, 3), 220, dtype=np.uint8)
    import cv2

    cv2.circle(frame, (50, 40), 22, (0, 0, 255), 5)
    assert RiskEngine._speed_sign_visual_score(frame, [25, 15, 75, 65]) >= 0.025


def test_close_speed_sign_requires_ring_and_classifier_agreement() -> None:
    local_config = {
        **CONFIG,
        "risk": {
            **CONFIG["risk"],
            "speed_sign_max_area_ratio": 0.025,
            "speed_sign_close_max_area_ratio": 0.06,
            "speed_sign_close_red_ring_min": 0.08,
            "speed_sign_close_classifier_confidence_min": 0.90,
        },
    }
    engine = RiskEngine(local_config)
    bbox = [190.0, 42.0, 281.0, 131.0]
    shape = (343, 500)
    assert not engine._valid_speed_sign_geometry(bbox, shape)
    assert not engine._valid_speed_sign_geometry(
        bbox, shape, visual_score=0.01, classifier_confidence=0.99
    )
    assert engine._valid_speed_sign_geometry(
        bbox, shape, visual_score=0.55, classifier_confidence=0.99
    )


def test_audio_drops_expired_event_without_speaking() -> None:
    lifecycle: list[tuple[str, str | None]] = []
    manager = AudioManager(
        CONFIG,
        lambda _event, status, reason: lifecycle.append((status, reason)),
    )
    spoken: list[str] = []
    manager._speak = lambda message: spoken.append(message)  # type: ignore[method-assign]
    manager.start()
    manager.submit(
        {
            "event_id": "old-event",
            "event_type": "speed_sign",
            "severity": "advisory",
            "message": "Biển cũ",
            "audio_action": "tts",
            "expires_at": time.time() - 1,
            "supersede_key": "speed_sign",
        }
    )
    time.sleep(0.35)
    manager.stop()
    assert spoken == []
    assert ("dropped_stale", "expired") in lifecycle


def test_paired_red_lamps_produce_brake_cue() -> None:
    frame = np.zeros((120, 200, 3), dtype=np.uint8)
    frame[48:62, 55:75, 2] = 255
    frame[48:62, 125:145, 2] = 255
    score = RiskEngine._brake_light_score(frame, [40, 20, 160, 100])
    assert score >= 0.42


def test_audio_silence_prefix_preserves_waveform(tmp_path) -> None:
    import wave

    source = tmp_path / "source.wav"
    destination = tmp_path / "destination.wav"
    with wave.open(str(source), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16_000)
        writer.writeframes(b"\x01\x00" * 160)
    AudioManager._prepend_silence(source, destination, 100)
    with wave.open(str(destination), "rb") as reader:
        assert reader.getnframes() == 1_600 + 160


def test_audio_backend_failure_is_not_reported_as_completed() -> None:
    lifecycle: list[tuple[str, str | None]] = []
    manager = AudioManager(
        CONFIG,
        lambda _event, status, reason: lifecycle.append((status, reason)),
    )

    def fail_speech(_message: str) -> str:
        raise RuntimeError("audio-device-unavailable")

    manager._speak = fail_speech  # type: ignore[method-assign]
    manager.start()
    manager.submit(
        {
            "event_id": "failed-speed-event",
            "event_type": "speed_sign",
            "severity": "advisory",
            "message": "Giới hạn tốc độ 80",
            "audio_action": "tts",
            "expires_at": time.time() + 2,
            "supersede_key": "speed_sign:80",
        }
    )
    time.sleep(0.35)
    manager.stop()
    assert manager.completed == 0
    assert manager.error == "audio-device-unavailable"
    assert any(status == "failed" for status, _reason in lifecycle)
    assert not any(status == "completed" for status, _reason in lifecycle)


def test_audio_metrics_meet_software_queue_gate() -> None:
    manager = AudioManager(CONFIG)
    manager._speak = lambda _message: "test-provider"  # type: ignore[method-assign]
    manager.start()
    for index in range(100):
        manager.submit({
            "event_id": f"event-{index}",
            "event_type": "test_advisory",
            "severity": "advisory",
            "message": f"Thông báo {index}",
            "spoken_message": f"Thông báo {index}",
            "audio_action": "tts",
            "expires_at": time.time() + 10,
            "supersede_key": f"test:{index}",
        })
    manager._queue.join()
    status = manager.status()
    manager.stop()
    assert status["completion_rate"] >= 0.99
    assert status["stale_rate"] < 0.02
    assert status["start_latency_p95_ms"] <= 750.0


def test_no_entry_message_expresses_direction_uncertainty() -> None:
    policy = policy_for_label("No Entry")
    assert policy is not None
    assert policy.severity == "advisory"
    assert "kiểm tra" in policy.message.lower()
    assert "hướng" in policy.message.lower()


def test_vnext_no_entry_is_visual_only_until_orientation_is_confirmed() -> None:
    message, audio_eligible, evidence = resolve_sign_message(
        "No Entry", {"confidence": 0.99}
    )
    assert message == "Biển cấm đi vào; kiểm tra hướng."
    assert audio_eligible is False
    assert evidence["orientation_status"] == "unknown"

    opposite_message, opposite_audio, opposite_evidence = resolve_sign_message(
        "No Entry",
        {
            "orientation_status": "opposite",
            "orientation_confidence": 0.91,
        },
    )
    assert opposite_message == "Cấm đi vào chiều đối diện."
    assert opposite_audio is True
    assert opposite_evidence["orientation_status"] == "opposite_direction"


def test_sign_tracking_accepts_zoom_when_center_remains_stable() -> None:
    engine = RiskEngine(CONFIG)
    previous = [100.0, 100.0, 130.0, 130.0]
    zoomed = [92.0, 92.0, 138.0, 138.0]
    assert engine._traffic_sign_track_stable(previous, zoomed, (480, 640))


def test_sign_tracking_rejects_distant_box_with_same_class() -> None:
    engine = RiskEngine(CONFIG)
    assert not engine._traffic_sign_track_stable(
        [100.0, 100.0, 130.0, 130.0],
        [400.0, 250.0, 430.0, 280.0],
        (480, 640),
    )
