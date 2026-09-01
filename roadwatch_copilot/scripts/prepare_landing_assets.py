"""Prepare only allowlisted local preview media. Never uploads or trains."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'artifacts' / 'landing-tools'))
sys.path.insert(0, str(ROOT / 'backend'))
os.environ['ROADWATCH_ALERT_COPY_PROFILE'] = 'vnext'
OUT = ROOT / 'frontend' / 'landing-public'


def main() -> None:
    import imageio_ffmpeg
    from roadwatch.tts import PiperSynthesizer
    from roadwatch.alert_copy import fcw_message, vulnerable_message, speed_limit_message
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    media = OUT / 'media'
    media.mkdir(parents=True, exist_ok=True)
    manifest = {'version': '1.0', 'public_release': False,
                'permission': 'local_preview_only_pending_public_media_review', 'assets': []}
    def register(path: Path, source: str, kind: str, **extra):
        manifest['assets'].append({'file': str(path.relative_to(OUT)).replace('\\', '/'),
            'source': source, 'kind': kind, 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), **extra})
    # Original visual footage, no invented detections or incident labels.
    clips = [('day', 'test_video10.mp4', 0),
             ('dense', 'dashcam_vietnam_traffic_multi.mp4', 6),
             ('night', 'dashcam_vietnam_night.mp4', 0),
             ('rain', 'dashcam_vietnam_rain+night.mp4', 0)]
    for key, source, start in clips:
        source_path = ROOT / 'media' / source
        target = media / f'{key}.mp4'
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(start),
            '-i', str(source_path), '-t', '18', '-an', '-vf', 'scale=960:-2,fps=24',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '29', '-threads', '2',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)], check=True)
        poster = media / f'{key}.webp'
        subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-ss', '2',
            '-i', str(target), '-frames:v', '1', '-quality', '78', str(poster)], check=True)
        register(target, source, 'source_video', start_seconds=start, duration_seconds=18)
        register(poster, source, 'source_frame', source_seconds=start + 2)
        print(f'Prepared {key}: {target.stat().st_size} bytes', flush=True)
    logo = ROOT / 'data' / 'assets' / 'logo.png'
    # Mechanical format/size conversion; retains original project artwork.
    subprocess.run([ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(logo),
        '-vf', 'scale=144:-1', '-quality', '90', str(media / 'logo.webp')], check=True)
    register(media / 'logo.webp', 'data/assets/logo.png', 'project_logo')
    voice = PiperSynthesizer(cache_size=3)
    messages = [('collision', fcw_message('', 'phía trước', critical=True)),
                ('motorcycle', vulnerable_message('Xe máy', 'bên phải')),
                ('speed', speed_limit_message(60))]
    audio = []
    for key, text in messages:
        result = voice.synthesize(text)
        path = media / f'{key}.wav'
        path.write_bytes(result.wav)
        with wave.open(str(path), 'rb') as wav:
            duration = wav.getnframes() / wav.getframerate()
        audio.append({'id': key, 'text': text, 'url': f'/media/{key}.wav',
                      'duration': round(duration, 2), 'provider': result.provider})
        register(path, 'RoadWatch canonical vnext + Piper release', 'tts_sample',
                 text=text, model_sha256=result.voice_model_sha256)
    (media / 'audio.json').write_text(json.dumps(audio, ensure_ascii=False, indent=2), encoding='utf-8')
    report = json.loads((ROOT / 'reports' / 'benchmark-performance-release-20260829.json').read_text(encoding='utf-8'))
    # Public projection only; no local paths, credentials or event/user metadata.
    metric = report['metrics']
    projection = {'date': report['generated_at'], 'source': report['source'],
        'seconds': report['duration_seconds'], 'hardware': 'Windows · AMD Ryzen 5 / Radeon',
        'audio': 'off', 'profiles': report['profiles'],
        'metrics': {k:metric.get(k) for k in ['processed_fps','display_fps','warmup_ms']}}
    # Latency structure differs between report versions; copy only the known aggregate.
    projection['metrics']['latencies'] = {'end_to_end': metric.get('latencies', {}).get('end_to_end', {})}
    (media / 'benchmark.json').write_text(json.dumps(projection, ensure_ascii=False, indent=2), encoding='utf-8')
    if not (media / 'replays.json').exists():
        (media / 'replays.json').write_text('[]', encoding='utf-8')
    (OUT / 'media-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    docs = OUT / 'documents'
    docs.mkdir(exist_ok=True)
    for name in ['ROADWATCH_TECHNICAL_REPORT.md', 'PERFORMANCE_STREAMING_OPTIMIZATION_2026-08-29.md']:
        shutil.copy2(ROOT / 'docs' / name, docs / name)
    print('Local media ready. Public release requires rights/privacy review.', flush=True)


if __name__ == '__main__':
    main()
