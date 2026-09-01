from roadwatch.audio import AudioManager


def _config() -> dict:
    return {
        "audio": {
            "enabled": True,
            "output_owner": "server",
            "tts_enabled": True,
            "piper_voice": "missing.onnx",
        }
    }


def _event() -> dict:
    return {
        "event_id": "routing-event",
        "event_type": "fcw",
        "severity": "critical",
        "message": "Cảnh báo va chạm",
        "audio_action": "beep_tts",
        "expires_at": 9_999_999_999,
        "supersede_key": "fcw",
    }


def test_browser_owner_delegates_without_queue_or_server_playback(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_AUDIO_OUTPUT", "browser")
    manager = AudioManager(_config())
    event = _event()

    manager.submit(event)

    assert manager.server_output_enabled is False
    assert manager.status()["output_owner"] == "browser"
    assert manager.status()["browser_playback"] is True
    assert manager.status()["queue_size"] == 0
    assert event["audio_status"] == "delegated_browser"


def test_browser_owner_still_delegates_when_backend_audio_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_AUDIO_OUTPUT", "browser")
    config = _config()
    config["audio"]["enabled"] = False
    manager = AudioManager(config)

    event = _event()
    manager.submit(event)

    assert manager.status()["browser_playback"] is True
    assert manager.status()["server_playback"] is False
    assert event["audio_status"] == "delegated_browser"


def test_none_owner_does_not_play_or_queue(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_AUDIO_OUTPUT", "none")
    manager = AudioManager(_config())
    event = _event()

    manager.submit(event)

    assert manager.server_output_enabled is False
    assert manager.status()["output_owner"] == "none"
    assert manager.status()["server_playback"] is False
    assert manager.status()["browser_playback"] is False
    assert manager.status()["queue_size"] == 0
    assert event["audio_status"] == "not_played"


def test_default_owner_keeps_native_server_fallback(monkeypatch) -> None:
    monkeypatch.delenv("ROADWATCH_AUDIO_OUTPUT", raising=False)
    manager = AudioManager(_config())

    assert manager.output_owner == "server"
    assert manager.server_output_enabled is True


def test_context_beep_is_delegated_without_tts_or_server_queue(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_AUDIO_OUTPUT", "browser")
    manager = AudioManager(_config())
    event = {
        "event_id": "context-event",
        "event_type": "traffic_context_attention",
        "severity": "informational",
        "message": "Giao thông đông; cảnh báo chọn lọc.",
        "spoken_message": "",
        "audio_action": "context_beep",
        "expires_at": 9_999_999_999,
        "supersede_key": "traffic_context_attention",
    }

    manager.submit(event)

    assert manager.status()["queue_size"] == 0
    assert event["audio_status"] == "delegated_browser"


def test_same_event_is_claimed_only_once(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_AUDIO_OUTPUT", "browser")
    manager = AudioManager(_config())
    event = _event()

    manager.submit(event)
    manager.submit(dict(event))

    assert event["audio_status"] == "delegated_browser"
    assert manager.status()["queue_size"] == 0


def test_same_message_is_not_queued_twice_with_different_event_ids(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_AUDIO_OUTPUT", "server")
    manager = AudioManager(_config())
    first = _event()
    second = {**_event(), "event_id": "routing-event-2"}

    manager.submit(first)
    manager.submit(second)

    assert manager.status()["queue_size"] == 1
    assert first["audio_claim_id"].startswith("server:")
    assert first["audio_play_count"] == 1
    assert second["audio_status"] == "suppressed_duplicate"
