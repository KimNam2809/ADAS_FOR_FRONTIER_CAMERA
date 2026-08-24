import threading

import pytest

from roadwatch.pipeline import RoadWatchService


class AliveThread:
    def is_alive(self) -> bool:
        return True


class AudioStub:
    def __init__(self) -> None:
        self.reasons: list[str] = []

    def clear_pending(self, reason: str) -> None:
        self.reasons.append(reason)


def service() -> RoadWatchService:
    instance = object.__new__(RoadWatchService)
    instance._thread = AliveThread()
    instance._state_lock = threading.RLock()
    instance._control_lock = threading.RLock()
    instance._pause = threading.Event()
    instance._pending_seek_seconds = None
    instance._status = {
        "running": True,
        "seekable": True,
        "source_time": 100.0,
        "duration_seconds": 300.0,
        "mode": "replay",
        "playback": "playing",
    }
    instance.audio = AudioStub()
    return instance


def test_pause_resume_preserves_position_and_clears_pending_audio() -> None:
    instance = service()
    instance.pause()
    assert instance._pause.is_set()
    assert instance._status["source_time"] == 100.0
    assert instance._status["playback"] == "paused"
    assert instance.audio.reasons == ["playback_paused"]

    instance.resume()
    assert not instance._pause.is_set()
    assert instance._status["playback"] == "playing"
    assert instance._status["source_time"] == 100.0


def test_seek_supports_absolute_relative_and_duration_clamping() -> None:
    instance = service()
    assert instance.seek(25.0) == 25.0
    assert instance._pending_seek_seconds == 25.0
    assert instance.seek(-15.0, relative=True) == 85.0
    assert instance.seek(999.0) == 300.0
    assert instance.seek(-999.0) == 0.0
    assert instance.audio.reasons == ["playback_seek"] * 4


def test_camera_source_rejects_pause_and_seek() -> None:
    instance = service()
    instance._status["seekable"] = False
    with pytest.raises(RuntimeError):
        instance.pause()
    with pytest.raises(RuntimeError):
        instance.seek(10.0)


def test_mjpeg_stream_is_bound_to_session_identity() -> None:
    instance = service()
    instance._frame_lock = threading.RLock()
    instance._latest_jpeg = b"new-session-frame"
    instance._status["session_id"] = "session-b"

    stale_stream = instance.mjpeg("session-a")
    with pytest.raises(StopIteration):
        next(stale_stream)

    current_stream = instance.mjpeg("session-b")
    assert b"new-session-frame" in next(current_stream)
