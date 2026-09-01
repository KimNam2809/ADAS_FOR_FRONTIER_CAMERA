from __future__ import annotations

import hashlib
import logging
import math
import os
import queue
import shutil
import struct
import threading
import time
import wave
from pathlib import Path
from typing import Any, Callable

from .config import DATA_ROOT, PROJECT_ROOT
from .tts import (
    DEFAULT_VOICE,
    DEFAULT_VOICE_NAME,
    PIPER_CACHE_NAMESPACE,
    normalize_tts_text,
    piper_voice_fingerprint,
)


LOGGER = logging.getLogger(__name__)


class AudioManager:
    def __init__(
        self,
        config: dict[str, Any],
        lifecycle_callback: Callable[[dict[str, Any], str, str | None], None] | None = None,
    ) -> None:
        self.config = config["audio"]
        self.enabled = bool(self.config.get("enabled", True))
        requested_owner = os.getenv(
            "ROADWATCH_AUDIO_OUTPUT",
            str(self.config.get("output_owner", "server")),
        ).strip().lower()
        if requested_owner not in {"server", "browser", "none"}:
            LOGGER.warning(
                "ROADWATCH_AUDIO_OUTPUT=%r không hợp lệ; dùng server output",
                requested_owner,
            )
            requested_owner = "server"
        self.output_owner = requested_owner
        self._queue: queue.PriorityQueue[tuple[int, int, dict[str, Any]]] = queue.PriorityQueue()
        self._sequence = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._tts_engine: Any | None = None
        self._piper_voice: Any | None = None
        self._vieneu_provider: Any | None = None
        self._piper_provider: Any | None = None
        self.last_action = "idle"
        self.error: str | None = None
        self._latest_by_key: dict[str, str] = {}
        self._claimed_event_ids: set[str] = set()
        self._recent_audio_by_key: dict[str, float] = {}
        self._lifecycle_callback = lifecycle_callback
        self.dropped_stale = 0
        self.completed = 0
        self.submitted = 0
        self.failed = 0
        self._start_latencies_ms: list[float] = []
        self.last_provider: str | None = None
        self.last_spoken_message: str | None = None
        self.fallbacks = 0
        self.last_fallback_reason: str | None = None

    def start(self) -> None:
        if not self.server_output_enabled or (self._thread and self._thread.is_alive()):
            return
        self._stop.clear()
        self._drain_queue()
        self._latest_by_key.clear()
        self._claimed_event_ids.clear()
        self._recent_audio_by_key.clear()
        self._thread = threading.Thread(target=self._worker, name="roadwatch-audio", daemon=True)
        self._thread.start()

    def submit(self, event: dict[str, Any]) -> None:
        if event.get("audio_action") not in {"tts", "beep_tts", "context_beep"}:
            return
        event_id = str(event.get("event_id", ""))
        try:
            message_key = normalize_tts_text(
                str(
                    event.get("spoken_message")
                    or event.get("message")
                    or event.get("event_type")
                    or ""
                )
            ).casefold()
        except ValueError as exc:
            self._notify(event, "failed", f"invalid_tts_message:{exc}")
            self.failed += 1
            return
        now = time.monotonic()
        dedupe_seconds = float(self.config.get("dedupe_window_seconds", 2.0))
        if event_id and event_id in self._claimed_event_ids:
            self._notify(event, "suppressed_duplicate", "duplicate_event_claim")
            return
        previous_at = self._recent_audio_by_key.get(message_key)
        if previous_at is not None and now - previous_at < dedupe_seconds:
            self._notify(event, "suppressed_duplicate", "duplicate_audio_key")
            return
        if event_id:
            self._claimed_event_ids.add(event_id)
            if len(self._claimed_event_ids) > 4096:
                self._claimed_event_ids.clear()
        self._recent_audio_by_key[message_key] = now
        event["canonical_audio_key"] = str(
            event.get("canonical_audio_key") or f"{event.get('event_type', 'tts')}:{message_key}"
        )
        event["audio_claim_id"] = f"{self.output_owner}:{event_id or message_key}"
        event["audio_play_count"] = int(event.get("audio_play_count", 0) or 0) + 1
        if self.output_owner == "browser":
            # The browser fetches the event-specific WAV and owns both beep and
            # speech. Mark delegation for audit purposes, but never enqueue a
            # second physical playback on the backend host.
            self._notify(event, "delegated_browser")
            return
        if self.output_owner == "none" or not self.enabled:
            self._notify(event, "not_played", "audio_output_disabled")
            return
        self._sequence += 1
        priority = 0 if event["severity"] == "critical" else 1
        key = str(event.get("supersede_key") or event.get("cooldown_key") or event["event_type"])
        self._latest_by_key[key] = str(event["event_id"])
        event["audio_queued_at"] = time.time()
        self.submitted += 1
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
                latency_ms = max(
                    0.0, (time.time() - float(event.get("audio_queued_at", time.time()))) * 1000.0
                )
                self._start_latencies_ms.append(latency_ms)
                if event["audio_action"] == "context_beep":
                    self._context_beep()
                elif event["audio_action"] == "beep_tts":
                    self._beep(self.config.get("beep_pattern"))
                if event["audio_action"] in {"tts", "beep_tts"} and self.config.get("tts_enabled", True):
                    message = normalize_tts_text(event.get("spoken_message", event["message"]))
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
                self.failed += 1
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

    @staticmethod
    def _context_beep() -> None:
        """Play two soft attention tones without invoking the TTS provider."""

        cache_dir = DATA_ROOT / "audio" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        wav_path = cache_dir / "context_attention_v1.wav"
        if not wav_path.exists():
            sample_rate = 16_000
            tone_plan = ((920, 70), (0, 110), (1100, 70))
            frames = bytearray()
            amplitude = int(32767 * 0.20)
            for frequency, duration_ms in tone_plan:
                samples = int(sample_rate * duration_ms / 1000)
                for index in range(samples):
                    value = 0 if frequency == 0 else int(
                        amplitude * math.sin(2 * math.pi * frequency * index / sample_rate)
                    )
                    frames.extend(struct.pack("<h", value))
            with wave.open(str(wav_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(frames)
        AudioManager._play_wav(wav_path, "context-beep")

    def _speak(self, message: str) -> str:
        message = normalize_tts_text(message)
        requested_provider = os.getenv(
            "ROADWATCH_TTS_PROVIDER", str(self.config.get("provider", "piper"))
        ).strip().lower()
        if requested_provider == "vieneu":
            return self._speak_vieneu(message)

        configured_voice = os.getenv(
            "ROADWATCH_TTS_VOICE", str(self.config.get("piper_voice", DEFAULT_VOICE))
        )
        voice = Path(configured_voice)
        if not voice.is_absolute():
            voice = PROJECT_ROOT / voice
        voice = voice.resolve()
        voice_config = Path(f"{voice}.json")
        if voice.exists() and voice_config.exists():
            fingerprint = piper_voice_fingerprint(str(voice))
            cache_dir = DATA_ROOT / "audio" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            # The model/config fingerprint is part of the key. A voice swap or
            # regenerated config must never reuse an old WAV for the same text.
            cache_key = hashlib.sha256(
                f"{PIPER_CACHE_NAMESPACE}:{fingerprint['model_sha256']}:{fingerprint['config_sha256']}:{message}".encode("utf-8")
            ).hexdigest()[:20]
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
            return self._play_wav(wav_path, "piper-vi")
        raise FileNotFoundError(
            "Thiếu Piper voice tiếng Việt. Hãy chạy .\\scripts\\setup.ps1 "
            "để tải vi_VN-vais1000-medium trước khi phát cảnh báo."
        )

    def _speak_vieneu(self, message: str) -> str:
        """Play the VieNeu candidate locally, falling back to Piper on failure."""

        message = normalize_tts_text(message)
        from .tts import PiperSynthesizer
        from .tts_vieneu import VieNeuSynthesizer

        if self._vieneu_provider is None:
            self._vieneu_provider = VieNeuSynthesizer()
        try:
            result = self._vieneu_provider.synthesize(message)
            self.last_fallback_reason = None
        except Exception as candidate_exc:
            self.fallbacks += 1
            self.last_fallback_reason = (
                str(candidate_exc).replace("\r", " ").replace("\n", " ")[:300]
            )
            if self._piper_provider is None:
                self._piper_provider = PiperSynthesizer(
                    os.getenv(
                        "ROADWATCH_TTS_VOICE",
                        self.config.get("piper_voice", DEFAULT_VOICE),
                    ),
                    voice_name=os.getenv(
                        "ROADWATCH_TTS_VOICE_NAME",
                        self.config.get("piper_voice_name", DEFAULT_VOICE_NAME),
                    ),
                )
            result = self._piper_provider.synthesize(message)

        cache_dir = DATA_ROOT / "audio" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = hashlib.sha256(
            f"vieneu-v1:{result.provider}:{message}".encode("utf-8")
        ).hexdigest()[:20]
        wav_path = cache_dir / f"{cache_key}.wav"
        if not wav_path.exists():
            raw_path = cache_dir / f"{cache_key}.raw.wav"
            raw_path.write_bytes(result.wav)
            self._prepend_silence(raw_path, wav_path, 140)
            raw_path.unlink(missing_ok=True)
        return self._play_wav(wav_path, result.provider)

    @staticmethod
    def _play_wav(wav_path: Any, provider: str) -> str:
        if os.name == "nt":
            import winsound

            winsound.PlaySound(str(wav_path), winsound.SND_FILENAME)
            return f"{provider}/winsound"
        if shutil.which("aplay"):
            import subprocess

            subprocess.run(["aplay", "-q", str(wav_path)], check=True, timeout=12)
            return f"{provider}/aplay"
        raise RuntimeError("Đã tạo WAV nhưng không tìm thấy thiết bị phát aplay")

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
        ordered_latency = sorted(self._start_latencies_ms)
        p95_index = max(0, int((len(ordered_latency) - 1) * 0.95))
        p95_latency = ordered_latency[p95_index] if ordered_latency else 0.0
        configured_provider = os.getenv(
            "ROADWATCH_TTS_PROVIDER", str(self.config.get("provider", "piper"))
        ).strip().lower()
        voice_name = os.getenv(
            "ROADWATCH_TTS_VOICE_NAME",
            str(self.config.get("piper_voice_name", DEFAULT_VOICE_NAME)),
        ).strip() or DEFAULT_VOICE_NAME
        configured_voice = os.getenv(
            "ROADWATCH_TTS_VOICE", str(self.config.get("piper_voice", DEFAULT_VOICE))
        )
        voice_path = Path(configured_voice)
        if not voice_path.is_absolute():
            voice_path = PROJECT_ROOT / voice_path
        voice_path = voice_path.resolve()
        provider_name = (
            "vieneu/Minh Triết"
            if configured_provider == "vieneu"
            else "piper-vi"
            if voice_path.exists() and Path(f"{voice_path}.json").exists()
            else "piper-missing"
        )
        return {
            "enabled": self.enabled,
            "output_owner": self.output_owner,
            "server_playback": self.server_output_enabled,
            "browser_playback": self.output_owner == "browser",
            "playback_mode": "single_owner",
            "provider": provider_name,
            "voice_name": voice_name,
            "last_action": self.last_action,
            "queue_size": self._queue.qsize(),
            "completed": self.completed,
            "submitted": self.submitted,
            "failed": self.failed,
            "dropped_stale": self.dropped_stale,
            "completion_rate": round(self.completed / max(self.submitted, 1), 4),
            "stale_rate": round(self.dropped_stale / max(self.submitted, 1), 4),
            "start_latency_p95_ms": round(p95_latency, 3),
            "tts_enabled": bool(self.config.get("tts_enabled", True)),
            "last_provider": self.last_provider,
            "last_spoken_message": self.last_spoken_message,
            "fallbacks": self.fallbacks,
            "last_fallback_reason": self.last_fallback_reason,
            "voice_model": voice_path.name,
            "voice_model_sha256": (
                piper_voice_fingerprint(str(voice_path)).get("model_sha256")
                if voice_path.exists() and Path(f"{voice_path}.json").exists()
                else None
            ),
            "voice_config_sha256": (
                piper_voice_fingerprint(str(voice_path)).get("config_sha256")
                if voice_path.exists() and Path(f"{voice_path}.json").exists()
                else None
            ),
            "cache_namespace": PIPER_CACHE_NAMESPACE,
            "error": self.error,
        }

    @property
    def server_output_enabled(self) -> bool:
        """Whether this process is allowed to drive a physical speaker."""

        return self.enabled and self.output_owner == "server"

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        self._drain_queue()

    def clear_pending(self, reason: str = "playback_control") -> None:
        """Drop queued speech when replay time changes or pauses."""

        while True:
            try:
                _, _, event = self._queue.get_nowait()
                self.dropped_stale += 1
                self._notify(event, "dropped_stale", reason)
                self._queue.task_done()
            except queue.Empty:
                return

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
