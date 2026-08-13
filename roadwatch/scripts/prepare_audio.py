from __future__ import annotations

import hashlib
import sys
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from roadwatch.config import DATA_ROOT  # noqa: E402


MESSAGES = [
    "Nguy cơ va chạm phía trước. Hãy chú ý.",
    "Cảnh báo lệch làn bên trái.",
    "Cảnh báo lệch làn bên phải.",
]
for actor in ("Ô tô", "Xe máy", "Xe đạp", "Xe buýt", "Xe tải", "Người đi bộ"):
    for location in ("phía trước", "phía trước bên trái", "phía trước bên phải"):
        MESSAGES.append(f"{actor} {location}, đang tiến gần. Hãy chú ý.")
        MESSAGES.append(f"{actor} {location}, chú ý khoảng cách an toàn.")
        MESSAGES.append(f"{actor} {location} có xu hướng nhập làn.")
for speed in (10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120):
    MESSAGES.append(f"Đã nhận diện biển giới hạn tốc độ {speed} ki-lô-mét một giờ.")


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
