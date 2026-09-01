"""Bootstrap RoadWatch demo assets from the public Google Drive folders.

The script is intentionally idempotent and never deletes local files. It only
downloads a folder when the local runtime is missing required model files or
has no media video yet. A cloned project can therefore use the default Drive
assets, or skip this script and supply its own assets manually.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "external_assets.json"


def _load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("external assets config must be a JSON object")
    return value


def _existing_names(root: Path, suffixes: Iterable[str]) -> list[Path]:
    if not root.exists():
        return []
    normalized = {suffix.lower() for suffix in suffixes}
    return [item for item in root.rglob("*") if item.is_file() and item.suffix.lower() in normalized]


def _missing_required_models(models_dir: Path, required: list[str]) -> list[str]:
    missing: list[str] = []
    for filename in required:
        if not any(candidate.name == filename for candidate in models_dir.rglob("*")):
            missing.append(filename)
    return missing


def _promote_expected_files(root: Path, filenames: Iterable[str]) -> None:
    """Flatten an unexpected Drive subfolder for runtime-known filenames.

    gdown normally writes a folder's files directly to the requested output,
    but a shared Drive folder can contain one extra directory level. Moving
    only known runtime filenames keeps the runtime contract deterministic and
    never overwrites an existing local file.
    """

    root.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        destination = root / filename
        if destination.exists():
            continue
        candidates = [item for item in root.rglob(filename) if item != destination and item.is_file()]
        if len(candidates) == 1:
            shutil.copy2(candidates[0], destination)


def _download_folder(url: str, output: Path) -> None:
    try:
        import gdown  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised by setup failure
        raise RuntimeError(
            "Thiếu gdown. Hãy chạy .venv\\Scripts\\python.exe -m pip install -r requirements-assets.txt"
        ) from exc
    output.mkdir(parents=True, exist_ok=True)
    result = gdown.download_folder(
        url=url,
        output=str(output),
        quiet=False,
        use_cookies=False,
        remaining_ok=True,
    )
    if result is None:
        raise RuntimeError(f"Không tải được Google Drive folder: {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--models-dir", type=Path, default=PROJECT_ROOT / "models")
    parser.add_argument("--media-dir", type=Path, default=PROJECT_ROOT / "media")
    parser.add_argument("--skip-models", action="store_true")
    parser.add_argument("--skip-media", action="store_true")
    parser.add_argument("--force", action="store_true", help="Download even when local files exist")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = _load_config(args.config.resolve())
    distribution = config.get("distribution", {})
    models_url = str(distribution.get("models_drive_folder", "")).strip()
    media_url = str(distribution.get("media_drive_folder", "")).strip()
    required_models = [str(name) for name in config.get("runtime_required_models", [])]

    models_dir = args.models_dir.resolve()
    media_dir = args.media_dir.resolve()
    missing_models = _missing_required_models(models_dir, required_models)
    local_videos = _existing_names(media_dir, (".mp4", ".mov", ".mkv", ".avi", ".webm"))
    download_models = not args.skip_models and bool(models_url) and (args.force or bool(missing_models))
    download_media = not args.skip_media and bool(media_url) and (args.force or not local_videos)

    plan = {
        "models_dir": str(models_dir),
        "media_dir": str(media_dir),
        "missing_required_models": missing_models,
        "local_video_count": len(local_videos),
        "download_models": download_models,
        "download_media": download_media,
        "dry_run": args.dry_run,
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    if args.dry_run:
        return 0

    if download_models:
        print("RoadWatch assets: tải models từ Google Drive...")
        _download_folder(models_url, models_dir)
        _promote_expected_files(models_dir, required_models)
    else:
        print("RoadWatch assets: giữ models local hiện có hoặc đã được skip.")

    if download_media:
        print("RoadWatch assets: tải media từ Google Drive...")
        _download_folder(media_url, media_dir)
    else:
        print("RoadWatch assets: giữ media local hiện có hoặc đã được skip.")

    remaining = _missing_required_models(models_dir, required_models)
    if remaining and not args.skip_models:
        print(
            "Cảnh báo: vẫn thiếu model runtime sau bootstrap: " + ", ".join(remaining),
            file=sys.stderr,
        )
        print("Bạn có thể đặt thủ công các file vào models/ theo README.md.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
