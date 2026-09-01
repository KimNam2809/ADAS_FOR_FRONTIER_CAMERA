from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import cv2

from .config import MEDIA_ROOT, PROJECT_ROOT


SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
_CONDITION_RULES = (
    ("rain_night", ("rain", "night")),
    ("night", ("night",)),
    ("rain", ("rain",)),
    ("dense_traffic", ("traffic_multi", "dense", "traffic")),
    ("day", ("day",)),
)


def _safe_relative(path: Path) -> str:
    return path.resolve().relative_to(MEDIA_ROOT.resolve()).as_posix()


def _condition_for(name: str) -> str:
    lowered = name.lower()
    for condition, tokens in _CONDITION_RULES:
        if all(token in lowered for token in tokens):
            return condition
    return "mixed"


def _probe_video(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    finally:
        capture.release()
    duration = frames / fps if fps > 0 and frames > 0 else 0.0
    return {
        "fps": round(fps, 3),
        "frame_count": frames,
        "width": width,
        "height": height,
        "duration_seconds": round(duration, 3),
    }


def _cached_result_key(path: Path) -> str:
    stat = path.stat()
    return hashlib.sha256(f"{_safe_relative(path)}:{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()


def media_catalog(include_probe: bool = True) -> list[dict[str, Any]]:
    """Return a stable, source-safe catalog for local and replay deployments.

    `source` is always relative to MEDIA_ROOT. It is the only value that the
    start endpoint should send back to ConfigManager.media_source().
    """
    remote_items: dict[str, dict[str, Any]] = {}
    if os.getenv("ROADWATCH_GCS_ASSET_BUCKET"):
        manifest_path = PROJECT_ROOT / "configs" / "cloud_assets.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for item in manifest.get("media", []):
                relative = Path(str(item["path"])).as_posix()
                remote_items[relative] = {
                    "name": Path(relative).name,
                    "source": relative,
                    "relative_source": relative,
                    "source_kind": "library",
                    "condition": _condition_for(Path(relative).stem),
                    "size_mb": float(item.get("size_mb", 0.0)),
                    "duration_seconds": float(item.get("duration_seconds", 0.0)),
                    "fps": float(item.get("fps", 0.0)),
                    "frame_count": int(item.get("frame_count", 0)),
                    "width": int(item.get("width", 0)),
                    "height": int(item.get("height", 0)),
                    "cached_result": False,
                    "storage_mode": "gcs_lazy",
                }
    result: list[dict[str, Any]] = []
    for path in sorted(MEDIA_ROOT.rglob("*")) if MEDIA_ROOT.exists() else []:
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
            continue
        relative = _safe_relative(path)
        item: dict[str, Any] = {
            "name": path.name,
            "source": relative,
            "relative_source": relative,
            "source_kind": "upload" if relative.startswith("uploads/") else "library",
            "condition": _condition_for(path.stem),
            "size_mb": round(path.stat().st_size / 1_048_576, 2),
            "cached_result": False,
            "cache_key": _cached_result_key(path),
        }
        if include_probe:
            item.update(_probe_video(path))
        result.append(item)
        remote_items.pop(relative, None)
    result.extend(remote_items[key] for key in sorted(remote_items))
    return result


def library_manifest() -> dict[str, Any]:
    items = media_catalog(include_probe=True)
    return {
        "schema_version": "roadwatch.library.v1",
        "root": "roadwatch/media",
        "items": items,
        "cached_results": "not_available_local_runtime",
    }


def write_library_manifest(path: Path) -> dict[str, Any]:
    manifest = library_manifest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
