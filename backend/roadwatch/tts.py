from __future__ import annotations

import hashlib
import io
import os
import re
import threading
import time
import urllib.error
import urllib.request
import wave
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable
from functools import lru_cache
from typing import Any, Callable, Protocol

from .alert_copy import (
    ambiguous_speed_message,
    combined_speed_limit_message,
    cross_traffic_message,
    cut_in_message,
    fcw_message,
    lead_braking_message,
    ldw_message,
    speed_limit_message,
    validate_alert_message,
    vulnerable_message,
)
from .config import PROJECT_ROOT


DEFAULT_VOICE = "voices/vi_VN-vais1000-medium.onnx"
DEFAULT_VOICE_NAME = "Trúc Ly"
MAX_TEXT_LENGTH = 240
PIPER_CACHE_NAMESPACE = "piper-v3"


@dataclass(frozen=True)
class TtsAudio:
    wav: bytes
    provider: str
    cache_hit: bool
    synthesis_ms: float
    fallback_reason: str | None = None
    voice_name: str | None = None
    voice_model_sha256: str | None = None


class TTSProvider(Protocol):
    """Small contract shared by Piper and optional Vietnamese TTS candidates."""

    @property
    def provider(self) -> str: ...

    def warmup(self, messages: Iterable[str] | None = None) -> None: ...

    def synthesize(self, text: str) -> TtsAudio: ...

    def status(self) -> dict[str, Any]: ...


def _collapse_adjacent_duplicate_tokens(text: str) -> str:
    """Repair a malformed repeated-token sentence before it reaches Piper.

    The normalizer is deliberately limited to adjacent duplicates. It does not
    rewrite valid Vietnamese wording or infer new alert content.
    """

    tokens = " ".join(str(text).split()).split(" ")
    result: list[str] = []
    previous_key = ""
    for token in tokens:
        key = re.sub(r"[^\wÀ-ỹĐđ]+", "", token, flags=re.UNICODE).casefold()
        if key and key == previous_key:
            continue
        result.append(token)
        if key:
            previous_key = key
    return " ".join(result)


def normalize_tts_text(text: str) -> str:
    """Return bounded Vietnamese text with adjacent duplicate tokens removed."""

    value = validate_alert_message(_collapse_adjacent_duplicate_tokens(text))
    if len(value) > MAX_TEXT_LENGTH:
        raise ValueError(f"Thông điệp TTS vượt {MAX_TEXT_LENGTH} ký tự")
    return value


# Backward-compatible private alias used by the optional VieNeu adapter.
_normalise_text = normalize_tts_text


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=8)
def piper_voice_fingerprint(voice_path: str) -> dict[str, Any]:
    """Read immutable Piper metadata once per process and return its fingerprint."""

    model = Path(voice_path).resolve()
    config_path = Path(f"{model}.json")
    if not model.is_file() or not config_path.is_file():
        raise FileNotFoundError(f"Thiếu Piper voice/config: {model.name}")
    import json

    metadata = json.loads(config_path.read_text(encoding="utf-8"))
    espeak_voice = str(metadata.get("espeak", {}).get("voice", ""))
    return {
        "model": model.name,
        "model_sha256": _sha256_file(model),
        "config_sha256": _sha256_file(config_path),
        "language": "vi_VN" if espeak_voice == "vi" else espeak_voice,
        "espeak_voice": espeak_voice,
        "sample_rate": int(metadata.get("audio", {}).get("sample_rate", 0)),
        "quality": str(metadata.get("audio", {}).get("quality", "")),
        "num_speakers": int(metadata.get("num_speakers", 1)),
        "speaker_id_map": metadata.get("speaker_id_map", {}),
        "cache_namespace": PIPER_CACHE_NAMESPACE,
    }


def default_alert_corpus() -> tuple[str, ...]:
    """Enumerate bounded RoadWatch messages so public TTS is cache-first."""

    from .signs import spoken_sign_messages

    labels = (
        "Người đi bộ",
        "Xe hai bánh",
        "Xe đạp",
        "Xe máy",
        "Ô tô",
        "Xe buýt",
        "Xe tải",
    )
    locations = ("phía trước", "bên trái", "bên phải")
    messages = set(spoken_sign_messages())
    messages.update({"Hãy chú ý.", fcw_message("", "phía trước", critical=True)})
    messages.update({"Cấm đi vào chiều đối diện.", "Cấm đi vào chiều này."})
    messages.update({ldw_message("trái"), ldw_message("phải")})
    for label in labels:
        for location in locations:
            messages.add(fcw_message(label, location))
            messages.add(vulnerable_message(label, location))
        for origin in locations[1:]:
            messages.add(cut_in_message(label, origin))
        for origin_side in ("left", "right", "front"):
            messages.add(cross_traffic_message(label, origin_side, "left_to_right"))
    for label in ("Ô tô", "Xe buýt", "Xe tải"):
        messages.add(lead_braking_message(label))
    messages.add(ambiguous_speed_message())
    messages.add(ambiguous_speed_message(minimum=True))
    messages.add(combined_speed_limit_message(80, 60))
    for speed in (30, 40, 50, 60, 80):
        messages.add(speed_limit_message(speed, minimum=True))
    return tuple(sorted(validate_alert_message(message) for message in messages))


class PiperSynthesizer:
    """Thread-safe Piper voice with a small bounded WAV cache."""

    def __init__(
        self,
        voice_path: str | Path | None = None,
        *,
        cache_size: int = 64,
        voice_factory: Callable[[str], Any] | None = None,
        voice_name: str | None = None,
    ) -> None:
        configured = voice_path or os.getenv("ROADWATCH_TTS_VOICE", DEFAULT_VOICE)
        path = Path(configured)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        self.voice_path = path.resolve()
        self.voice_name = (
            voice_name
            or os.getenv("ROADWATCH_TTS_VOICE_NAME", DEFAULT_VOICE_NAME)
        ).strip() or DEFAULT_VOICE_NAME
        self.cache_size = max(1, min(int(cache_size), 256))
        self._voice_factory = voice_factory
        self._voice: Any | None = None
        self._lock = threading.RLock()
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self.requests = 0
        self.cache_hits = 0
        self.syntheses = 0
        self.last_synthesis_ms = 0.0
        self.load_ms = 0.0
        self.error: str | None = None
        self.precache_target = 0

    @property
    def provider(self) -> str:
        return "piper/vi_VN-vais1000-medium"

    def available(self) -> bool:
        return self.voice_path.is_file() and Path(f"{self.voice_path}.json").is_file()

    def warmup(self, messages: Iterable[str] | None = None) -> None:
        with self._lock:
            self._load_voice()
        # Loading the ONNX session alone does not execute its first graph or
        # initialise Vietnamese phonemisation. Prime both during Cloud Run
        # startup so the first real road hazard never pays that cold cost.
        corpus = tuple(messages or ("Hãy chú ý.",))
        self.precache_target = len(corpus)
        for message in corpus:
            self.synthesize(message)

    def _load_voice(self) -> Any:
        if self._voice is not None:
            return self._voice
        if not self.available():
            raise FileNotFoundError(f"Thiếu Piper voice/config: {self.voice_path.name}")
        started = time.perf_counter()
        if self._voice_factory is not None:
            self._voice = self._voice_factory(str(self.voice_path))
        else:
            from piper import PiperVoice

            self._voice = PiperVoice.load(str(self.voice_path))
        self.load_ms = (time.perf_counter() - started) * 1000.0
        return self._voice

    def synthesize(self, text: str) -> TtsAudio:
        message = normalize_tts_text(text)
        fingerprint = piper_voice_fingerprint(str(self.voice_path))
        key = hashlib.sha256(
            f"{PIPER_CACHE_NAMESPACE}:{fingerprint['model_sha256']}:{fingerprint['config_sha256']}:{message}".encode("utf-8")
        ).hexdigest()
        with self._lock:
            self.requests += 1
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                self.cache_hits += 1
                return TtsAudio(
                    cached,
                    self.provider,
                    True,
                    0.0,
                    voice_name=self.voice_name,
                    voice_model_sha256=fingerprint["model_sha256"],
                )

            started = time.perf_counter()
            output = io.BytesIO()
            with wave.open(output, "wb") as wav_file:
                self._load_voice().synthesize_wav(message, wav_file)
            audio = output.getvalue()
            if len(audio) < 44 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
                raise RuntimeError("Piper không sinh WAV hợp lệ")
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            self._cache[key] = audio
            self._cache.move_to_end(key)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)
            self.syntheses += 1
            self.last_synthesis_ms = elapsed_ms
            self.error = None
            return TtsAudio(
                audio,
                self.provider,
                False,
                elapsed_ms,
                voice_name=self.voice_name,
                voice_model_sha256=fingerprint["model_sha256"],
            )

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available(),
            "provider": self.provider,
            "voice": self.voice_path.name,
            "voice_name": self.voice_name,
            "voice_alias": self.voice_name,
            "language": "vi_VN",
            "sample_rate": 22050,
            "loaded": self._voice is not None,
            "requests": self.requests,
            "cache_hits": self.cache_hits,
            "syntheses": self.syntheses,
            "cache_entries": len(self._cache),
            "precache_target": self.precache_target,
            "load_ms": round(self.load_ms, 3),
            "last_synthesis_ms": round(self.last_synthesis_ms, 3),
            **(
                piper_voice_fingerprint(str(self.voice_path))
                if self.available()
                else {
                    "model": self.voice_path.name,
                    "model_sha256": None,
                    "config_sha256": None,
                    "quality": None,
                    "num_speakers": None,
                    "speaker_id_map": None,
                    "cache_namespace": PIPER_CACHE_NAMESPACE,
                }
            ),
            "error": self.error,
        }


class PiperGateway:
    """Route Piper/VieNeu without changing the event-ID TTS API.

    Piper remains the release default. VieNeu is deliberately local-only while
    it is a candidate: a cloud Piper endpoint must never be silently used when
    an operator selected the candidate provider.
    """

    def __init__(self) -> None:
        self.remote_url = os.getenv("ROADWATCH_TTS_SERVICE_URL", "").strip().rstrip("/")
        self.timeout_seconds = float(os.getenv("ROADWATCH_TTS_TIMEOUT_SECONDS", "8"))
        self.local = PiperSynthesizer()
        requested = os.getenv("ROADWATCH_TTS_PROVIDER", "piper").strip().lower()
        self.requested_provider = requested if requested in {"piper", "vieneu", "ab"} else "piper"
        self.configuration_error = (
            f"Không hỗ trợ ROADWATCH_TTS_PROVIDER={requested!r}; đã dùng piper"
            if requested not in {"piper", "vieneu", "ab"}
            else None
        )
        if self.requested_provider == "vieneu" and self.remote_url:
            self.configuration_error = (
                "VieNeu candidate chỉ chạy local; ROADWATCH_TTS_SERVICE_URL bị bỏ qua "
                "để tránh vô tình gọi Cloud Run Piper"
            )
        self._vieneu: TTSProvider | None = None
        self._credentials: Any | None = None
        self._credentials_lock = threading.Lock()
        self.requests = 0
        self.failed = 0
        self.fallbacks = 0
        self.last_latency_ms = 0.0
        self.error: str | None = None
        self.last_fallback_reason: str | None = None

    def _candidate(self) -> TTSProvider:
        if self._vieneu is None:
            from .tts_vieneu import VieNeuSynthesizer

            self._vieneu = VieNeuSynthesizer()
        return self._vieneu

    def warmup(self) -> None:
        """Warm the selected provider without pre-caching the public cloud by default."""

        if self.requested_provider == "vieneu":
            candidate = self._candidate()
            corpus = (
                default_alert_corpus()
                if os.getenv("ROADWATCH_TTS_PRECACHE", "0") == "1"
                else ("Hãy chú ý.",)
            )
            try:
                candidate.warmup(corpus)
            except Exception as candidate_exc:
                self.fallbacks += 1
                self.last_fallback_reason = (
                    str(candidate_exc).replace("\r", " ").replace("\n", " ")[:300]
                )
                # Startup remains available on the established release
                # provider. A subsequent event still records the same reason.
                self.local.warmup(("Hãy chú ý.",))
            return

        if self.remote_url:
            request = urllib.request.Request(
                f"{self.remote_url}/health",
                headers={"Authorization": f"Bearer {self._identity_token()}"},
                method="GET",
            )
            timeout = float(os.getenv("ROADWATCH_TTS_WARMUP_TIMEOUT_SECONDS", "180"))
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise RuntimeError(f"Piper warmup HTTP {response.status}")
                import json

                payload = json.loads(response.read().decode("utf-8"))
                if payload.get("status") != "ready":
                    raise RuntimeError(
                        f"Piper chưa sẵn sàng: {payload.get('error') or payload.get('status')}"
                    )

    def _identity_token(self) -> str:
        with self._credentials_lock:
            from google.auth.transport.requests import Request as GoogleAuthRequest
            from google.oauth2 import id_token

            if self._credentials is None:
                self._credentials = id_token.fetch_id_token_credentials(self.remote_url)
            if not self._credentials.valid:
                self._credentials.refresh(GoogleAuthRequest())
            if not self._credentials.token:
                raise RuntimeError("Không lấy được Cloud Run identity token cho Piper")
            return str(self._credentials.token)

    def _remote_synthesize(self, text: str) -> TtsAudio:
        import json

        request = urllib.request.Request(
            f"{self.remote_url}/synthesize",
            data=json.dumps({"text": text}, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._identity_token()}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                wav = response.read()
                return TtsAudio(
                    wav=wav,
                    provider=response.headers.get(
                        "X-RoadWatch-TTS-Provider", "piper/vi_VN-vais1000-medium"
                    ),
                    cache_hit=response.headers.get("X-RoadWatch-TTS-Cache", "miss") == "hit",
                    synthesis_ms=float(response.headers.get("X-RoadWatch-TTS-Ms", "0")),
                    voice_name=response.headers.get("X-RoadWatch-TTS-Voice", DEFAULT_VOICE_NAME),
                    voice_model_sha256=response.headers.get("X-RoadWatch-TTS-Model"),
                )
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"Piper service HTTP {exc.code}: {detail}") from exc

    def synthesize(self, text: str) -> TtsAudio:
        message = normalize_tts_text(text)
        self.requests += 1
        started = time.perf_counter()
        try:
            if self.requested_provider == "vieneu":
                try:
                    result = self._candidate().synthesize(message)
                    self.last_fallback_reason = None
                except Exception as candidate_exc:
                    # Safety/reliability rule: candidate failure returns the
                    # established local Piper release baseline, and the reason
                    # remains observable in status and the response header.
                    self.fallbacks += 1
                    self.last_fallback_reason = (
                        str(candidate_exc).replace("\r", " ").replace("\n", " ")[:300]
                    )
                    result = self.local.synthesize(message)
                    result = TtsAudio(
                        wav=result.wav,
                        provider=result.provider,
                        cache_hit=result.cache_hit,
                        synthesis_ms=result.synthesis_ms,
                        fallback_reason=self.last_fallback_reason,
                        voice_name=result.voice_name,
                        voice_model_sha256=result.voice_model_sha256,
                    )
            else:
                result = (
                    self._remote_synthesize(message)
                    if self.remote_url
                    else self.local.synthesize(message)
                )
            self.last_latency_ms = (time.perf_counter() - started) * 1000.0
            self.error = None
            return result
        except Exception as exc:
            self.failed += 1
            self.error = str(exc)
            raise

    def status(self) -> dict[str, Any]:
        candidate_status: dict[str, Any] | None = None
        if self.requested_provider == "vieneu":
            candidate_status = self._candidate().status()
        local_available = bool(self.remote_url) or self.local.available()
        return {
            "available": (
                bool(candidate_status and candidate_status["available"]) or self.local.available()
                if self.requested_provider == "vieneu" and candidate_status
                else local_available
            ),
            "provider": (
                "vieneu/Minh Triết"
                if self.requested_provider == "vieneu"
                else "piper/vi_VN-vais1000-medium"
            ),
            "requested_provider": self.requested_provider,
            "mode": (
                "local_candidate"
                if self.requested_provider == "vieneu"
                else "dedicated_cloud_service" if self.remote_url else "local"
            ),
            "language": "vi_VN",
            "voice_name": (
                self.local.status().get("voice_name", DEFAULT_VOICE_NAME)
                if self.requested_provider != "vieneu"
                else DEFAULT_VOICE_NAME
            ),
            "voice_model": self.local.status().get("model", Path(DEFAULT_VOICE).name),
            "voice_model_sha256": self.local.status().get("model_sha256"),
            "voice_config_sha256": self.local.status().get("config_sha256"),
            "sample_rate": self.local.status().get("sample_rate", 22050),
            "num_speakers": self.local.status().get("num_speakers", 1),
            "speaker_id_map": self.local.status().get("speaker_id_map", {}),
            "cache_namespace": PIPER_CACHE_NAMESPACE,
            "requests": self.requests,
            "failed": self.failed,
            "fallbacks": self.fallbacks,
            "last_latency_ms": round(self.last_latency_ms, 3),
            "error": self.error or self.configuration_error,
            "last_fallback_reason": self.last_fallback_reason,
            "fallback_available": self.local.available(),
            "local": self.local.status() if not self.remote_url else None,
            "candidate": candidate_status,
        }
