"""Capture bounded real local replays; never change production config or train.

Frames are sampled at 12 Hz wall-clock. This is a screen replay, not a camera
FPS benchmark. No audio is emitted and no synthetic events are inserted.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'artifacts/landing-tools')]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=18)
    parser.add_argument('--runtime', default='directml', choices=['directml', 'cpu'])
    args = parser.parse_args()
    os.environ.update(ROADWATCH_DISABLE_AUDIO='1', ROADWATCH_AUDIO_OUTPUT='none',
        ROADWATCH_RUNTIME=args.runtime, ROADWATCH_TRAFFIC_CONTEXT_MODE='enforce')
    import imageio_ffmpeg
    from roadwatch.config import ConfigManager
    from roadwatch.storage import Storage
    from roadwatch.pipeline import RoadWatchService
    out = ROOT / 'frontend/landing-public/media'
    evidence = ROOT / 'reports/landing-v1'
    evidence.mkdir(parents=True, exist_ok=True)
    config = ConfigManager(runtime_path=evidence / 'capture-config-unused.json')
    config.update({'audio': {'enabled': False}, 'slm': {'enabled': False},
                   'app': {'loop_video': False}}, persist=False)
    service = RoadWatchService(config, Storage(evidence / 'events.db'))
    catalog = []
    clips = [('dense', 'dashcam_vietnam_traffic_multi.mp4', 6),
             ('day', 'test_video10.mp4', 0), ('night', 'dashcam_vietnam_night.mp4', 0),
             ('rain', 'dashcam_vietnam_rain+night.mp4', 0)]
    try:
        for key, source, start in clips:
            service.start(source, start_seconds=start, duration_seconds=args.seconds + 5)
            deadline = time.monotonic() + 150
            first = None
            while time.monotonic() < deadline:
                status = service.status()
                with service._frame_lock:
                    first = service._latest_jpeg
                if first and status.get('stage') == 'inference':
                    break
                if not service.is_running:
                    raise RuntimeError(f'Capture stopped before inference: {status.get("error")}')
                time.sleep(.1)
            if not first:
                raise RuntimeError('Capture warmup timeout')
            target = out / f'{key}-replay.mp4'
            process = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner',
                '-loglevel', 'error', '-y', '-f', 'image2pipe', '-vcodec', 'mjpeg',
                '-framerate', '12', '-i', '-', '-an', '-vf', 'scale=960:-2',
                '-c:v', 'libx264', '-crf', '28', '-preset', 'fast', '-threads', '2',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(target)], stdin=subprocess.PIPE)
            seen = set()
            events = []
            began = time.monotonic()
            try:
                for frame in range(args.seconds * 12):
                    status = service.status()
                    with service._frame_lock:
                        jpeg = service._latest_jpeg or first
                    process.stdin.write(jpeg)
                    for event in reversed(status.get('events', [])):
                        identifier = event.get('event_id') or event.get('id')
                        if identifier in seen:
                            continue
                        seen.add(identifier)
                        events.append({'time': round(frame / 12, 2),
                            'source_time': status.get('source_time', 0),
                            'event_type': event.get('event_type', ''),
                            'message': event.get('canonical_message') or event.get('message') or event.get('spoken_message', ''),
                            'severity': event.get('severity', ''), 'audio_action': event.get('audio_action', ''),
                            'risk_score': event.get('risk_score'), 'suppression_reason': event.get('suppression_reason')})
                    delay = began + (frame + 1) / 12 - time.monotonic()
                    if delay > 0:
                        time.sleep(delay)
            finally:
                process.stdin.close()
                process.wait(timeout=30)
                service.stop()
            if process.returncode:
                raise RuntimeError('Replay encoder failed')
            catalog.append({'id': key, 'video': f'/media/{key}-replay.mp4', 'duration': args.seconds,
                'source': source, 'models': ['YOLO11n', 'Sign v2', 'YOLOP'],
                'capture_fps': 12, 'kind': 'recorded_local_pipeline', 'events': events})
            (out / 'replays.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
            (evidence / f'{key}-status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'{key}: {len(events)} real events, {target.stat().st_size} bytes', flush=True)
    finally:
        service.close()


if __name__ == '__main__':
    main()
