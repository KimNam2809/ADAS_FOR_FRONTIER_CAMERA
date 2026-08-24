import threading
from collections import deque

import pytest

from roadwatch.pipeline import RoadWatchService
from roadwatch.config import ConfigManager


class AliveThread:
    def is_alive(self) -> bool:
        return True


class AudioStub:
    def __init__(self) -> None:
        self.reasons: list[str] = []

    def clear_pending(self, reason: str) -> None:
        self.reasons.append(reason)

    def start(self) -> None:
        return None


class ResetStub:
    def reset(self) -> None:
        return None


class PerceptionStub:
    def status(self) -> dict:
        return {}


class ConfigStub:
    def snapshot(self) -> dict:
        return {"app": {"default_source": "test_video1.mp4"}}


class DormantThread:
    def __init__(self, **_: object) -> None:
        return None

    def start(self) -> None:
        return None

    def is_alive(self) -> bool:
        return False


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


def test_start_resets_visual_state_before_new_video(monkeypatch) -> None:
    instance = object.__new__(RoadWatchService)
    instance.config_manager = ConfigStub()
    instance._thread = None
    instance._state_lock = threading.RLock()
    instance._frame_lock = threading.RLock()
    instance._control_lock = threading.RLock()
    instance._stop = threading.Event()
    instance._pause = threading.Event()
    instance._pending_seek_seconds = None
    instance._latest_jpeg = b"stale-frame"
    instance._recent_events = deque([{"event_id": "old"}], maxlen=20)
    instance._active_events = {"old": {"event_id": "old"}}
    instance._status = {
        "running": False,
        "frame_id": 26,
        "source_fps": 30,
        "source_time": 10.0,
        "duration_seconds": 60.0,
        "lane": {"quality": 0.9, "offset": 0.2},
        "tracks": [{"track_id": 7}],
        "signs": [{"label": "80"}],
        "events": [{"event_id": "old"}],
    }
    instance.tracker = ResetStub()
    instance.kinematics = ResetStub()
    instance.risk = ResetStub()
    instance.governor = ResetStub()
    instance.audio = AudioStub()
    instance.perception = PerceptionStub()

    monkeypatch.setattr(ConfigManager, "media_source", staticmethod(lambda _: "C:/media/test_video10.mp4"))
    monkeypatch.setattr("roadwatch.pipeline.threading.Thread", DormantThread)

    instance.start("test_video10.mp4")

    assert instance._status["source_key"] == "test_video10.mp4"
    assert instance._status["frame_id"] == 0
    assert instance._status["source_time"] == 0.0
    assert instance._status["tracks"] == []
    assert instance._status["signs"] == []
    assert instance._status["lane"] == {"quality": 0, "offset": 0}
    assert instance._latest_jpeg is None
