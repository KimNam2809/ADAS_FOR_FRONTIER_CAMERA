from __future__ import annotations

import time
from pathlib import Path

from roadwatch.slm import SlmExplanationWorker, build_chat, build_payload, validate_output
from roadwatch.storage import Storage


def _config() -> dict:
    return {
        "risk": {
            "fcw_warning": 0.56,
            "fcw_critical": 0.78,
            "fcw_width_ratio_min": 0.18,
            "fcw_relative_rate_min": 0.20,
            "hazard_confirmation_frames": 3,
        },
        "slm": {
            "enabled": False,
            "model_dir": "qwen2.5-0.5b",
            "max_new_tokens": 128,
            "queue_size": 8,
        },
    }


def _fcw_event() -> dict:
    return {
        "event_type": "fcw",
        "severity": "warning",
        "message": "Cảnh báo xe phía trước.",
        "confidence": 0.88,
        "risk_score": 0.73,
        "object_id": 4,
        "location": "phía trước",
        "event_id": "fcw-test-1",
        "evidence": {
            "object_label": "truck",
            "path_conflict": True,
            "box_width_ratio": 0.24,
            "relative_closing_rate_per_s": 0.40,
            "confirmation_frames_required": 3,
        },
    }


def test_fcw_payload_uses_rule_evidence_and_omits_internal_fields() -> None:
    payload = build_payload(_fcw_event(), _config())
    assert payload == {
        "event": "fcw",
        "level": "warning",
        "object": "xe tải",
        "track": 4,
        "position": "phía trước",
        "conflict": True,
        "bbox_pct": 24,
        "bbox_min_pct": 18,
        "closing_rate_s": 0.4,
        "closing_min_s": 0.2,
        "risk": 0.73,
        "risk_min": 0.56,
        "frames": 3,
    }
    prompt, current = build_chat(_fcw_event(), _config())
    assert current == payload
    assert "image_space" not in prompt
    assert "trigger_path" not in prompt


def test_validator_accepts_grounded_one_sentence_and_rejects_bad_output() -> None:
    payload = build_payload(_fcw_event(), _config())
    good = (
        "FCW warning được kích hoạt cho xe tải thuộc track 4 ở phía trước vì đối tượng "
        "xung đột với quỹ đạo dự kiến, bounding box chiếm 24% chiều rộng frame vượt ngưỡng "
        "18%, mức tiếp cận tương đối đạt 0,40/s vượt ngưỡng 0,20/s, risk score đạt 0,73 "
        "vượt ngưỡng 0,56 và điều kiện được duy trì trong 3 frame xác nhận."
    )
    valid, score, failed = validate_output(payload, good)
    assert valid
    assert score >= 90
    assert not failed

    invalid, _, failed = validate_output(
        payload,
        "FCW do path_conflict, TTC 0.75 giây; hãy phanh ngay.",
    )
    assert not invalid
    assert {"no_raw_keys", "no_hallucinated_physics", "no_action_advice"} <= set(failed)


def test_storage_persists_async_slm_lifecycle(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "events.db")
    event = {
        **_fcw_event(),
        "created_at": time.time(),
        "audio_action": "hud",
    }
    storage.add_event(event)
    storage.update_event_slm(
        "fcw-test-1", "ready", "Giải thích hợp lệ.", 123.4, None
    )
    saved = storage.get_event_by_uuid("fcw-test-1")
    assert saved is not None
    assert saved["slm_status"] == "ready"
    assert saved["slm_explanation"] == "Giải thích hợp lệ."
    assert saved["slm_latency_ms"] == 123.4
    storage.close()


def test_disabled_worker_is_non_blocking() -> None:
    results: list[tuple[str, object]] = []
    worker = SlmExplanationWorker(_config(), lambda event_id, result: results.append((event_id, result)))
    assert worker.status()["state"] == "disabled"
    assert worker.submit(_fcw_event()) == "disabled"
    assert results == []
    worker.close()
