from __future__ import annotations

import hashlib
import logging
import os
import queue
import shutil
import threading
import time
import wave
from typing import Any, Callable

from .config import DATA_ROOT, PROJECT_ROOT


LOGGER = logging.getLogger(__name__)


class AudioManager:
    def __init__(
        self,
        config: dict[str, Any],
        lifecycle_callback: Callable[[dict[str, Any], str, str | None], None] | None = None,
    ) -> None:
        self.config = config["audio"]
        self.enabled = bool(self.config.get("enabled", True))
        self._queue: queue.PriorityQueue[tuple[int, int, dict[str, Any]]] = queue.PriorityQueue()
        self._sequence = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tts_engine: Any | None = None
        self._piper_voice: Any | None = None
        self.last_action = "idle"
        self.error: str | None = None
        self._latest_by_key: dict[str, str] = {}
        self._lifecycle_callback = lifecycle_callback
        self.dropped_stale = 0
        self.completed = 0
        self.last_provider: str | None = None
        self.last_spoken_message: str | None = None

    def start(self) -> None:
        if not self.enabled or (self._thread and self._thread.is_alive()):
            return
        self._stop.clear()
        self._drain_queue()
        self._latest_by_key.clear()
        self._thread = threading.Thread(target=self._worker, name="roadwatch-audio", daemon=True)
        self._thread.start()

    def submit(self, event: dict[str, Any]) -> None:
        if not self.enabled or event.get("audio_action") not in {"tts", "beep_tts"}:
            return
        self._sequence += 1
        priority = 0 if event["severity"] == "critical" else 1
        key = str(event.get("supersede_key") or event.get("cooldown_key") or event["event_type"])
        self._latest_by_key[key] = str(event["event_id"])
        self._notify(event, "queued")
        self._queue.put((priority, self._sequence, event))

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                _, _, event = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                key = str(event.get("supersede_key") or event.get("cooldown_key") or event["event_type"])
                if self._latest_by_key.get(key) != str(event.get("event_id")):
                    self.dropped_stale += 1
                    self._notify(event, "dropped_stale", "superseded")
                    continue
                if float(event.get("expires_at", float("inf"))) < time.time():
                    self.dropped_stale += 1
                    self._notify(event, "dropped_stale", "expired")
                    continue
                self._notify(event, "playing")
                if event["audio_action"] == "beep_tts":
                    self._beep(self.config.get("beep_pattern"))
                if self.config.get("tts_enabled", True):
                    message = event.get("spoken_message", event["message"])
                    self.last_provider = self._speak(message) or "test-or-custom"
                    self.last_spoken_message = message
                elif event["audio_action"] in {"tts", "beep_tts"}:
                    raise RuntimeError("TTS đang bị tắt trong cấu hình audio.tts_enabled")
                self.last_action = f"finished:{event['event_type']}"
                self.error = None
                self.completed += 1
                self._notify(event, "completed")
            except Exception as exc:  # pragma: no cover - audio device dependent
                self.error = str(exc)
                self._notify(event, "failed", str(exc))
                LOGGER.exception("Audio output failed")
            finally:
                self._queue.task_done()

    @staticmethod
    def _beep(pattern: list[list[int]] | None = None) -> None:
        if os.name == "nt":
            import winsound
            for frequency, duration in pattern or [[1450, 180]]:
                if int(frequency) <= 0:
                    time.sleep(int(duration) / 1000.0)
                else:
                    winsound.Beep(int(frequency), int(duration))

    def _speak(self, message: str) -> str:
        voice = (PROJECT_ROOT / self.config.get("piper_voice", "")).resolve()
        if voice.exists():
            cache_dir = DATA_ROOT / "audio" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            # Cache version v2 includes a short silence prefix. Some vehicle/
            # laptop audio devices wake late and otherwise clip the first word.
            cache_key = hashlib.sha256(f"v2:{message}".encode("utf-8")).hexdigest()[:20]
            wav_path = cache_dir / f"{cache_key}.wav"
            if self._piper_voice is None:
                from piper import PiperVoice

                self._piper_voice = PiperVoice.load(str(voice))
            if not wav_path.exists():
                raw_path = cache_dir / f"{cache_key}.raw.wav"
                with wave.open(str(raw_path), "wb") as wav_file:
                    self._piper_voice.synthesize_wav(message, wav_file)
                self._prepend_silence(raw_path, wav_path, 140)
                raw_path.unlink(missing_ok=True)
            if os.name == "nt":
                import winsound

                winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
                return "piper-vi/winsound"
            elif shutil.which("aplay"):
                import subprocess

                subprocess.run(["aplay", "-q", str(wav_path)], check=True, timeout=12)
                return "piper-vi/aplay"
            raise RuntimeError("Đã tạo WAV bằng Piper nhưng không tìm thấy thiết bị phát aplay")
        if os.name == "nt" and (shutil.which("python") or True):
            if self._tts_engine is None:
                try:
                    import pyttsx3

                    self._tts_engine = pyttsx3.init()
                    self._tts_engine.setProperty("rate", 185)
                except Exception:
                    self._tts_engine = False
            if self._tts_engine:
                self._tts_engine.say(message)
                self._tts_engine.runAndWait()
                return "system/pyttsx3"
            raise RuntimeError("Không thể khởi tạo TTS hệ thống pyttsx3")
        raise RuntimeError("Không tìm thấy giọng Piper hoặc TTS hệ thống tương thích")

    @staticmethod
    def _prepend_silence(source: Any, destination: Any, duration_ms: int) -> None:
        with wave.open(str(source), "rb") as reader:
            params = reader.getparams()
            frames = reader.readframes(reader.getnframes())
        silence_frames = int(params.framerate * duration_ms / 1000)
        silence = b"\x00" * silence_frames * params.nchannels * params.sampwidth
        with wave.open(str(destination), "wb") as writer:
            writer.setparams(params)
            writer.writeframes(silence + frames)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": "piper-vi" if (PROJECT_ROOT / self.config.get("piper_voice", "")).exists() else "system-fallback",
            "last_action": self.last_action,
            "queue_size": self._queue.qsize(),
            "completed": self.completed,
            "dropped_stale": self.dropped_stale,
            "tts_enabled": bool(self.config.get("tts_enabled", True)),
            "last_provider": self.last_provider,
            "last_spoken_message": self.last_spoken_message,
            "error": self.error,
        }

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self._drain_queue()

    def _notify(self, event: dict[str, Any], status: str, reason: str | None = None) -> None:
        event["audio_status"] = status
        if reason:
            event["suppression_reason"] = reason
        if self._lifecycle_callback:
            try:
                self._lifecycle_callback(event, status, reason)
            except Exception:  # pragma: no cover - persistence must not stop audio
                LOGGER.exception("Không thể ghi audio lifecycle")

    def _drain_queue(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                return
