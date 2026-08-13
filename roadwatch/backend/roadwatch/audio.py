from __future__ import annotations

import hashlib
import logging
import os
import queue
import shutil
import threading
import wave
from typing import Any

from .config import DATA_ROOT, PROJECT_ROOT


LOGGER = logging.getLogger(__name__)


class AudioManager:
    def __init__(self, config: dict[str, Any]) -> None:
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

    def start(self) -> None:
        if not self.enabled or (self._thread and self._thread.is_alive()):
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, name="roadwatch-audio", daemon=True)
        self._thread.start()

    def submit(self, event: dict[str, Any]) -> None:
        if not self.enabled or event.get("audio_action") not in {"tts", "beep_tts"}:
            return
        self._sequence += 1
        priority = 0 if event["severity"] == "critical" else 1
        self._queue.put((priority, self._sequence, event))

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                _, _, event = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            try:
                if event["audio_action"] == "beep_tts":
                    self._beep()
                if self.config.get("tts_enabled", True):
                    self._speak(event["message"])
                self.last_action = f"finished:{event['event_type']}"
            except Exception as exc:  # pragma: no cover - audio device dependent
                self.error = str(exc)
                LOGGER.exception("Audio output failed")
            finally:
                self._queue.task_done()

    @staticmethod
    def _beep() -> None:
        if os.name == "nt":
            import winsound

            winsound.Beep(1450, 180)

    def _speak(self, message: str) -> None:
        voice = (PROJECT_ROOT / self.config.get("piper_voice", "")).resolve()
        if voice.exists():
            cache_dir = DATA_ROOT / "audio" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_key = hashlib.sha256(message.encode("utf-8")).hexdigest()[:20]
            wav_path = cache_dir / f"{cache_key}.wav"
            if self._piper_voice is None:
                from piper import PiperVoice

                self._piper_voice = PiperVoice.load(str(voice))
            if not wav_path.exists():
                with wave.open(str(wav_path), "wb") as wav_file:
                    self._piper_voice.synthesize_wav(message, wav_file)
            if os.name == "nt":
                import winsound

                winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
            elif shutil.which("aplay"):
                import subprocess

                subprocess.run(["aplay", "-q", str(wav_path)], check=False, timeout=12)
            return
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

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": "piper-vi" if (PROJECT_ROOT / self.config.get("piper_voice", "")).exists() else "system-fallback",
            "last_action": self.last_action,
            "queue_size": self._queue.qsize(),
            "error": self.error,
        }

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
