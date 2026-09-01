from __future__ import annotations

import io
import wave
from pathlib import Path

from fastapi.testclient import TestClient

import roadwatch.audio as audio_module
from roadwatch.alert_copy import (
    alert_word_count,
    alert_word_limit,
    cross_traffic_message,
    fcw_message,
    lead_braking_message,
    ldw_message,
    vulnerable_message,
)
from roadwatch.audio import AudioManager
from roadwatch.api import create_app
from roadwatch.tts import (
    PiperGateway,
    PiperSynthesizer,
    TtsAudio,
    default_alert_corpus,
    normalize_tts_text,
    piper_voice_fingerprint,
)
from roadwatch.tts_vieneu import VieNeuSynthesizer


class FakeVoice:
    def __init__(self) -> None:
        self.calls = 0

    def synthesize_wav(self, text: str, wav_file: wave.Wave_write) -> None:
        self.calls += 1
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(22050)
        wav_file.writeframes(b"\x00\x00" * max(100, len(text) * 20))


class FakeVieNeuEngine:
    def __init__(self) -> None:
        self.infer_calls: list[tuple[str, str]] = []

    def infer(self, text: str, *, voice: str) -> object:
        self.infer_calls.append((text, voice))
        return text

    def save(self, _audio: object, path: str) -> None:
        with wave.open(path, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(48_000)
            writer.writeframes(b"\x00\x00" * 240)


class BrokenCandidate:
    provider = "vieneu/Minh Triết"

    def synthesize(self, _text: str) -> TtsAudio:
        raise RuntimeError("candidate-not-ready")

    def status(self) -> dict[str, object]:
        return {"available": True, "provider": self.provider}

    def warmup(self, _messages=None) -> None:
        return None


def test_piper_synthesizer_returns_valid_wav_and_caches(tmp_path: Path) -> None:
    model = tmp_path / "vi_VN-test.onnx"
    model.write_bytes(b"model")
    Path(f"{model}.json").write_text("{}", encoding="utf-8")
    voice = FakeVoice()
    synthesizer = PiperSynthesizer(model, voice_factory=lambda _: voice)

    first = synthesizer.synthesize("Hãy chú ý.")
    second = synthesizer.synthesize("  Hãy   chú ý.  ")

    assert first.wav[:4] == b"RIFF"
    assert first.wav[8:12] == b"WAVE"
    assert first.provider == "piper/vi_VN-vais1000-medium"
    assert first.voice_name == "Trúc Ly"
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.wav == first.wav
    assert voice.calls == 1


def test_tts_normalizes_adjacent_repeated_tokens() -> None:
    assert normalize_tts_text("Cảnh cảnh báo báo va va chạm chạm") == "Cảnh báo va chạm"


def test_piper_cache_fingerprint_includes_model_and_config(tmp_path: Path) -> None:
    model = tmp_path / "vi_VN-test.onnx"
    model.write_bytes(b"model-v1")
    config = Path(f"{model}.json")
    config.write_text(
        '{"audio":{"sample_rate":22050,"quality":"medium"},'
        '"espeak":{"voice":"vi"},"num_speakers":1,"speaker_id_map":{}}',
        encoding="utf-8",
    )

    fingerprint = piper_voice_fingerprint(str(model))

    assert fingerprint["language"] == "vi_VN"
    assert fingerprint["espeak_voice"] == "vi"
    assert fingerprint["sample_rate"] == 22050
    assert fingerprint["quality"] == "medium"
    assert fingerprint["num_speakers"] == 1
    assert fingerprint["speaker_id_map"] == {}
    assert len(fingerprint["model_sha256"]) == 64
    assert len(fingerprint["config_sha256"]) == 64


def test_warmup_executes_graph_and_primes_vietnamese_phrase(tmp_path: Path) -> None:
    model = tmp_path / "vi_VN-test.onnx"
    model.write_bytes(b"model")
    Path(f"{model}.json").write_text("{}", encoding="utf-8")
    voice = FakeVoice()
    synthesizer = PiperSynthesizer(model, voice_factory=lambda _: voice)

    synthesizer.warmup()
    result = synthesizer.synthesize("Hãy chú ý.")

    assert voice.calls == 1
    assert result.cache_hit is True
    assert synthesizer.status()["loaded"] is True
    assert synthesizer.status()["voice_name"] == "Trúc Ly"


def test_default_alert_corpus_contains_speed_fcw_and_lane_messages() -> None:
    corpus = default_alert_corpus()

    assert "Cảnh báo va chạm" in corpus
    assert "Cảnh báo lệch làn bên phải." in corpus
    assert "Giới hạn 60 ki-lô-mét/giờ phía trước." in corpus
    assert "Xe máy cắt ngang từ bên trái." in corpus
    assert "Người đi bộ đang cắt ngang từ trái sang phải." in corpus
    assert all(alert_word_count(message) <= alert_word_limit() for message in corpus)
    assert len(corpus) == len(set(corpus))
    assert len(corpus) <= 256


def test_vnext_driver_copy_matches_approved_wording() -> None:
    assert fcw_message("Ô tô", "bên trái") == "Ô tô bên trái; giảm tốc độ."
    assert vulnerable_message("Người đi bộ", "phía trước") == (
        "Người đi bộ phía trước; giảm tốc độ."
    )
    assert lead_braking_message("Ô tô") == (
        "Ô tô phía trước đang giảm tốc. Hãy chú ý."
    )
    assert cross_traffic_message("Ô tô", "right", "right_to_left") == (
        "Ô tô cắt ngang từ bên phải."
    )
    assert cross_traffic_message("Người đi bộ", "left", "left_to_right") == (
        "Người đi bộ đang cắt ngang từ trái sang phải."
    )
    assert ldw_message("phải") == "Cảnh báo lệch làn bên phải."


def test_legacy_copy_profile_restores_previous_dynamic_messages(monkeypatch) -> None:
    monkeypatch.setenv("ROADWATCH_ALERT_COPY_PROFILE", "legacy")

    assert fcw_message("Ô tô", "phía trước", critical=True) == (
        "Cảnh báo va chạm phía trước!"
    )
    assert cross_traffic_message("Xe máy", "left", "left_to_right") == (
        "Xe máy cắt trái sang phải."
    )


def test_vieneu_candidate_returns_48khz_wav_and_caches() -> None:
    engine = FakeVieNeuEngine()
    synthesizer = VieNeuSynthesizer(engine_factory=lambda **_kwargs: engine)

    first = synthesizer.synthesize("Tối đa 60 ki-lô-mét/giờ.")
    second = synthesizer.synthesize("  Tối đa 60 ki-lô-mét/giờ.  ")

    assert first.wav[:4] == b"RIFF"
    assert first.provider == "vieneu/Minh Triết"
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert len(engine.infer_calls) == 1
    assert engine.infer_calls[0][1] == "Minh Triết"
    with wave.open(io.BytesIO(first.wav), "rb") as reader:
        assert reader.getframerate() == 48_000
        assert reader.getcomptype() == "NONE"
    assert synthesizer.status()["sample_rate"] == 48_000


def test_vieneu_gateway_falls_back_to_piper_and_exposes_reason(tmp_path: Path, monkeypatch) -> None:
    model = tmp_path / "vi_VN-test.onnx"
    model.write_bytes(b"model")
    Path(f"{model}.json").write_text("{}", encoding="utf-8")
    piper = PiperSynthesizer(model, voice_factory=lambda _: FakeVoice())
    monkeypatch.setenv("ROADWATCH_TTS_PROVIDER", "vieneu")
    gateway = PiperGateway()
    gateway._vieneu = BrokenCandidate()
    gateway.local = piper

    result = gateway.synthesize("Hãy chú ý.")

    assert result.provider == "piper/vi_VN-vais1000-medium"
    assert result.fallback_reason == "candidate-not-ready"
    assert gateway.status()["fallbacks"] == 1
    assert gateway.status()["last_fallback_reason"] == "candidate-not-ready"


def test_native_audio_manager_can_play_vieneu_candidate_without_browser_voice(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("ROADWATCH_TTS_PROVIDER", "vieneu")
    monkeypatch.setattr(audio_module, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(
        AudioManager,
        "_play_wav",
        staticmethod(lambda _path, provider: f"{provider}/test-device"),
    )
    manager = AudioManager(
        {
            "audio": {
                "enabled": True,
                "tts_enabled": True,
                "provider": "auto",
                "piper_voice": "voices/vi_VN-vais1000-medium.onnx",
            }
        }
    )
    manager._vieneu_provider = VieNeuSynthesizer(
        engine_factory=lambda **_kwargs: FakeVieNeuEngine()
    )

    result = manager._speak("Hãy chú ý.")

    assert result == "vieneu/Minh Triết/test-device"
    assert list((tmp_path / "audio" / "cache").glob("*.wav"))


def test_tts_endpoint_only_synthesizes_server_event(tmp_path: Path) -> None:
    app = create_app(database_path=tmp_path / "tts-api.db")
    event_id = "event-vi-001"
    app.state.storage.add_event(
        {
            "created_at": 1.0,
            "event_type": "fcw",
            "severity": "critical",
            "message": "Cảnh báo va chạm phía trước!",
            "spoken_message": "Cảnh báo va chạm phía trước!",
            "confidence": 0.9,
            "risk_score": 0.95,
            "audio_action": "beep_tts",
            "event_id": event_id,
        }
    )
    app.state.tts_gateway.synthesize = lambda text: TtsAudio(
        wav=b"RIFF\x00\x00\x00\x00WAVEroadwatch",
        provider="piper/vi_VN-vais1000-medium",
        cache_hit=True,
        synthesis_ms=0.0,
    )

    with TestClient(app) as client:
        assert client.get(f"/api/tts/events/{event_id}.wav").status_code == 401
        login = client.post(
            "/api/auth/login", json={"username": "driver", "password": "driver123"}
        )
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        response = client.get(f"/api/tts/events/{event_id}.wav", headers=headers)
        missing = client.get("/api/tts/events/not-found.wav", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["x-roadwatch-tts-provider"] == "piper/vi_VN-vais1000-medium"
    assert response.headers["x-roadwatch-tts-cache"] == "hit"
    assert response.content[:4] == b"RIFF"
    assert missing.status_code == 404
