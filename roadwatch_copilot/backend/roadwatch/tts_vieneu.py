from __future__ import annotations

import hashlib
import importlib.util
import io
import os
import tempfile
import threading
import time
import wave
from collections import OrderedDict
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from .tts import MAX_TEXT_LENGTH, TtsAudio, _normalise_text


DEFAULT_MODEL_ID = "pnnbao-ump/VieNeu-TTS-v3-Turbo"
DEFAULT_VOICE = "Minh Triết"


class VieNeuSynthesizer:
    """Optional VieNeu Vietnamese TTS candidate.

    The adapter intentionally owns no browser or cloud fallback. It produces a
    validated PCM WAV and leaves fallback policy to ``PiperGateway``. Lazy
    loading keeps the default Piper path free of a VieNeu import/download.
    """

    def __init__(
        self,
        *,
        voice: str | None = None,
        model_id: str | None = None,
        backend: str | None = None,
        precision: str | None = None,
        cache_size: int = 256,
        engine_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.voice = voice or os.getenv("ROADWATCH_TTS_VOICE_NAME", DEFAULT_VOICE)
        self.model_id = model_id or os.getenv("ROADWATCH_VIENEU_MODEL", DEFAULT_MODEL_ID)
        self.backend = backend or os.getenv("ROADWATCH_TTS_BACKEND", "onnx")
        self.precision = precision or os.getenv("ROADWATCH_TTS_PRECISION", "int8")
        self.cache_size = max(1, min(int(cache_size), 512))
        self._engine_factory = engine_factory
        self._engine: Any | None = None
        self._lock = threading.RLock()
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self.requests = 0
        self.cache_hits = 0
        self.syntheses = 0
        self.last_synthesis_ms = 0.0
        self.load_ms = 0.0
        self.precache_target = 0
        self.error: str | None = None

    @property
    def provider(self) -> str:
        return f"vieneu/{self.voice}"

    def available(self) -> bool:
        """Check package availability without downloading weights."""

        return self._engine_factory is not None or importlib.util.find_spec("vieneu") is not None

    def warmup(self, messages: Iterable[str] | None = None) -> None:
        try:
            with self._lock:
                self._load_engine()
            corpus = tuple(messages or ("Hãy chú ý.",))
            self.precache_target = len(corpus)
            for message in corpus:
                self.synthesize(message)
        except Exception as exc:
            self.error = str(exc)[:300]
            raise

    def _load_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        if not self.available():
            raise ModuleNotFoundError(
                "Thiếu package VieNeu. Cài requirements-tts-vieneu.txt để chạy candidate."
            )

        started = time.perf_counter()
        if self._engine_factory is not None:
            self._engine = self._engine_factory(
                backend=self.backend,
                precision=self.precision,
                model_id=self.model_id,
            )
        else:
            from vieneu import Vieneu

            try:
                self._engine = Vieneu(
                    mode="v3turbo",
                    backbone_repo=self.model_id,
                    device="cpu",
                    backend=self.backend,
                    precision=self.precision,
                )
            except TypeError:
                # Keep compatibility with SDK builds that infer the model from
                # the package and expose only the backend constructor argument.
                self._engine = Vieneu(mode="v3turbo", backend=self.backend)
        self.load_ms = (time.perf_counter() - started) * 1000.0
        return self._engine

    @staticmethod
    def _validate_wav(audio: bytes) -> None:
        if len(audio) < 44 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
            raise RuntimeError("VieNeu không sinh WAV RIFF/WAVE hợp lệ")
        try:
            with wave.open(io.BytesIO(audio), "rb") as reader:
                if (
                    reader.getnchannels() < 1
                    or reader.getframerate() <= 0
                    or reader.getcomptype() != "NONE"
                    or reader.getsampwidth() != 2
                ):
                    raise RuntimeError("VieNeu sinh WAV có thông số audio không hợp lệ")
        except (wave.Error, EOFError) as exc:
            raise RuntimeError("VieNeu sinh WAV bị hỏng hoặc thiếu header") from exc

    def _save_audio(self, generated: Any) -> bytes:
        output_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(prefix="roadwatch-vieneu-", suffix=".wav", delete=False) as file:
                output_path = Path(file.name)
            self._load_engine().save(generated, str(output_path))
            audio = output_path.read_bytes()
        finally:
            if output_path is not None:
                output_path.unlink(missing_ok=True)
        self._validate_wav(audio)
        return audio

    def synthesize(self, text: str) -> TtsAudio:
        message = _normalise_text(text)
        if len(message) > MAX_TEXT_LENGTH:
            raise ValueError(f"Thông điệp TTS vượt {MAX_TEXT_LENGTH} ký tự")
        key = hashlib.sha256(
            f"v1:{self.model_id}:{self.voice}:{self.backend}:{self.precision}:{message}".encode(
                "utf-8"
            )
        ).hexdigest()
        with self._lock:
            self.requests += 1
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                self.cache_hits += 1
                return TtsAudio(cached, self.provider, True, 0.0)

            started = time.perf_counter()
            try:
                generated = self._load_engine().infer(message, voice=self.voice)
                audio = self._save_audio(generated)
            except Exception as exc:
                self.error = str(exc)[:300]
                raise
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            self._cache[key] = audio
            self._cache.move_to_end(key)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)
            self.syntheses += 1
            self.last_synthesis_ms = elapsed_ms
            self.error = None
            return TtsAudio(audio, self.provider, False, elapsed_ms)

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available(),
            "provider": self.provider,
            "model_id": self.model_id,
            "voice": self.voice,
            "language": "vi_VN",
            "sample_rate": 48_000,
            "backend": self.backend,
            "precision": self.precision,
            "loaded": self._engine is not None,
            "requests": self.requests,
            "cache_hits": self.cache_hits,
            "syntheses": self.syntheses,
            "cache_entries": len(self._cache),
            "precache_target": self.precache_target,
            "load_ms": round(self.load_ms, 3),
            "last_synthesis_ms": round(self.last_synthesis_ms, 3),
            "error": self.error,
            "voice_cloning": False,
        }
