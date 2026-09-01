"""Repeatable build/media audit; does not claim browser or human acceptance."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    dist = ROOT / 'frontend/dist-landing'
    assert (dist / 'index.html').is_file()
    manifest = json.loads((dist / 'media-manifest.json').read_text(encoding='utf-8'))
    for asset in manifest['assets']:
        path = (dist / asset['file']).resolve()
        assert path.is_relative_to(dist.resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == asset['sha256'], asset['file']
    scripts = list((dist / 'assets').glob('*.js'))
    styles = list((dist / 'assets').glob('*.css'))
    js_gzip = sum(len(gzip.compress(path.read_bytes())) for path in scripts)
    css_gzip = sum(len(gzip.compress(path.read_bytes())) for path in styles)
    replay = json.loads((dist / 'media/replays.json').read_text(encoding='utf-8'))
    for clip in replay:
        assert (dist / clip['video'].lstrip('/')).is_file()
        assert all(0 <= event['time'] <= clip['duration'] for event in clip['events'])
    results = {'version': '1.0', 'status': 'PASS_STATIC_BUILD_AUDIT',
        'js_gzip_bytes': js_gzip, 'css_gzip_bytes': css_gzip,
        'js_200kb_gate': js_gzip <= 200_000, 'manifest_hashes_verified': len(manifest['assets']),
        'replays': [{'id': r['id'], 'seconds': r['duration'], 'events': len(r['events'])} for r in replay],
        'dist_bytes': sum(p.stat().st_size for p in dist.rglob('*') if p.is_file()),
        'public_release': False, 'lcp_inp_cls': 'NOT_MEASURED',
        'human_listening_comprehension': 'PENDING'}
    target = ROOT / 'reports/landing-v1/build-audit.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
