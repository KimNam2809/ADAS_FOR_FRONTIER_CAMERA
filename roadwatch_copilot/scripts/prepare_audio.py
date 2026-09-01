from __future__ import annotations

import hashlib
import sys
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from roadwatch.config import DATA_ROOT  # noqa: E402
from roadwatch.tts import default_alert_corpus  # noqa: E402


MESSAGES = default_alert_corpus()


def main() -> int:
    try:
        from piper import PiperVoice
    except ImportError:
        print("Thiếu piper-tts. Hãy cài requirements.txt trước.")
        return 2
    voice_path = PROJECT_ROOT / "voices" / "vi_VN-vais1000-medium.onnx"
    if not voice_path.exists():
        print(f"Thiếu voice model: {voice_path}")
        return 2
    cache_dir = DATA_ROOT / "audio" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    voice = PiperVoice.load(str(voice_path))
    generated = 0
    for message in MESSAGES:
        key = hashlib.sha256(message.encode("utf-8")).hexdigest()[:20]
        output = cache_dir / f"{key}.wav"
        if output.exists():
            continue
        with wave.open(str(output), "wb") as wav_file:
            voice.synthesize_wav(message, wav_file)
        generated += 1
        print(f"[{generated}] {message}")
    print(f"Audio cache sẵn sàng: {len(list(cache_dir.glob('*.wav')))} câu tại {cache_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
