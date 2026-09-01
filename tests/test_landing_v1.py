"""Landing release contract: isolated from live inference and existing HMI."""
import json
from pathlib import Path
import wave
import pytest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'frontend'


def test_separate_entry_and_build():
    config = (FRONTEND / 'vite.landing.config.ts').read_text(encoding='utf-8')
    assert "outDir: 'dist-landing'" in config
    assert "publicDir: 'landing-public'" in config
    assert 'landing-v1-main.tsx' in (FRONTEND / 'landing.html').read_text(encoding='utf-8')
    assert (FRONTEND / 'src/landing-main.tsx').exists()  # legacy kept


def test_no_live_inference_or_browser_voice_in_landing():
    source = (FRONTEND / 'src/landing/v1/LandingV1.tsx').read_text(encoding='utf-8')
    for forbidden in ['/api/status', '/api/session', '/api/tts', 'speechSynthesis', 'SpeechSynthesisUtterance', 'setInterval(']:
        assert forbidden not in source
    assert 'new Audio()' in source
    assert 'audioRef.current?.pause()' in source
    assert 'AbortController' in source
    assert 'KHÔNG ĐỔI NGƯỠNG THẬT' in source


def test_video_aspect_and_reduced_motion():
    css = (FRONTEND / 'src/landing/v1/landing-v1.css').read_text(encoding='utf-8')
    assert 'object-fit:contain' in css
    assert 'prefers-reduced-motion:reduce' in css
    assert ':focus-visible' in css


@pytest.mark.skipif(not (FRONTEND / 'landing-public/media/audio.json').exists(), reason='Local media not prepared')
def test_piper_samples_match_wav_and_have_no_empty_copy():
    media = FRONTEND / 'landing-public/media'
    samples = json.loads((media / 'audio.json').read_text(encoding='utf-8'))
    assert len(samples) == 3
    for sample in samples:
        assert sample['provider'] == 'piper/vi_VN-vais1000-medium'
        assert sample['text'].strip()
        with wave.open(str(media / Path(sample['url']).name), 'rb') as wav:
            assert wav.getframerate() == 22050
            assert wav.getnframes() > 0
            assert abs(wav.getnframes() / wav.getframerate() - sample['duration']) < .01


@pytest.mark.skipif(not (FRONTEND / 'landing-public/media/benchmark.json').exists(), reason='Local media not prepared')
def test_benchmark_is_exact_projection_not_marketing_number():
    original = json.loads((ROOT / 'reports/benchmark-performance-release-20260829.json').read_text(encoding='utf-8'))
    projected = json.loads((FRONTEND / 'landing-public/media/benchmark.json').read_text(encoding='utf-8'))
    for key in ['processed_fps', 'display_fps', 'warmup_ms']:
        assert projected['metrics'][key] == original['metrics'][key]
    assert projected['metrics']['latencies']['end_to_end'] == original['metrics']['latencies']['end_to_end']


def test_static_cloud_context_and_no_api_proxy():
    nginx = (ROOT / 'deploy/gcp/landing/nginx.conf').read_text(encoding='utf-8')
    assert 'location ^~ /api/ { return 404; }' in nginx
    assert 'proxy_pass' not in nginx
    package = (ROOT / 'scripts/package-landing.ps1').read_text(encoding='utf-8')
    assert 'PublicMediaApproved' in package
    assert 'gcloud run deploy' not in package
