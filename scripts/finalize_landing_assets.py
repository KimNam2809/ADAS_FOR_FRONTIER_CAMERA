"""Mechanical screenshot conversion and full static asset integrity manifest."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'artifacts/landing-tools'))


def main():
    import imageio_ffmpeg
    public = ROOT / 'frontend/landing-public'
    media = public / 'media'
    for role in ['driver', 'engineer']:
        source = media / f'{role}-capture.png'
        if source.exists():
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel',
                'error', '-y', '-i', str(source), '-vf', 'scale=1200:-2',
                '-quality', '83', str(media / f'{role}-capture.webp')], check=True)
    manifest_path = public / 'media-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    known = {asset['file']: asset for asset in manifest['assets']}
    files = []
    for path in sorted(public.rglob('*')):
        if not path.is_file() or path == manifest_path:
            continue
        relative = path.relative_to(public).as_posix()
        asset = known.get(relative, {'file': relative, 'source': 'RoadWatch local capture/generated documentation',
                                   'kind': 'local_evidence'})
        asset.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        files.append(asset)
    manifest['assets'] = files
    manifest['public_release'] = False
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{len(files)} assets fingerprinted. Public release still requires human approval.')


if __name__ == '__main__':
    main()
