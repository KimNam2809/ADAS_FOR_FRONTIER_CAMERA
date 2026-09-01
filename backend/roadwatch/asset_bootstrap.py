from __future__ import annotations

import json
import hashlib
import logging
import os
from pathlib import Path
from typing import Any

from .config import MEDIA_ROOT, MODEL_ROOT, PROJECT_ROOT, VOICE_ROOT


LOGGER = logging.getLogger(__name__)
MANIFEST_PATH = PROJECT_ROOT / "configs" / "cloud_assets.json"


def _verify_sha256(path: Path, expected: str | None) -> None:
    if not expected:
        return
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != expected.lower():
        raise ValueError(
            f"SHA-256 không khớp cho {path.name}: expected={expected}, actual={actual}"
        )


def _download_if_missing(bucket_name: str, item: dict[str, Any], root: Path, client: Any) -> str:
    relative = Path(str(item["path"]))
    target = (root / relative).resolve()
    if root.resolve() not in target.parents:
        raise ValueError(f"Cloud asset path vượt root: {relative}")
    if target.exists() and target.stat().st_size > 0:
        _verify_sha256(target, item.get("sha256"))
        return f"local:{target.name}"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.download")
    blob = client.bucket(bucket_name).blob(str(item["object"]))
    if not blob.exists(client):
        raise FileNotFoundError(f"Không tìm thấy GCS asset: gs://{bucket_name}/{item['object']}")
    blob.download_to_filename(str(temporary))
    _verify_sha256(temporary, item.get("sha256"))
    temporary.replace(target)
    return f"downloaded:{target.name}"


def bootstrap_assets() -> dict[str, Any]:
    """Materialize optional Cloud Storage assets before the pipeline can run.

    Local/offline runs are a no-op. The manifest is deliberately allowlisted so
    a public Cloud Run service cannot be tricked into downloading arbitrary
    object names from the bucket.
    """
    bucket_name = os.getenv("ROADWATCH_GCS_ASSET_BUCKET", "").strip()
    if not bucket_name:
        return {"enabled": False, "downloaded": [], "reason": "bucket_not_configured"}
    if not MANIFEST_PATH.exists():
        return {"enabled": False, "downloaded": [], "reason": "manifest_missing"}
    try:
        from google.cloud import storage

        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        client = storage.Client()
        downloaded: list[str] = []
        requested_groups = {
            item.strip()
            for item in os.getenv("ROADWATCH_ASSET_GROUPS", "models,media,voices").split(",")
            if item.strip()
        }
        roots = {"models": MODEL_ROOT, "media": MEDIA_ROOT, "voices": VOICE_ROOT}
        unknown_groups = requested_groups - roots.keys()
        if unknown_groups:
            raise ValueError(
                f"Cloud asset group không hợp lệ: {', '.join(sorted(unknown_groups))}"
            )
        requested_paths = {
            item.strip()
            for item in os.getenv("ROADWATCH_ASSET_PATHS", "").split(",")
            if item.strip()
        }
        available_paths = {
            str(item.get("path"))
            for group in requested_groups
            for item in manifest.get(group, [])
        }
        unknown_paths = requested_paths - available_paths
        if unknown_paths:
            raise ValueError(
                f"Cloud asset path không có trong manifest/group: {', '.join(sorted(unknown_paths))}"
            )
        for group, root in roots.items():
            if group not in requested_groups:
                continue
            for item in manifest.get(group, []):
                if requested_paths and str(item.get("path")) not in requested_paths:
                    continue
                downloaded.append(_download_if_missing(bucket_name, item, root, client))
        return {
            "enabled": True,
            "bucket": bucket_name,
            "groups": sorted(requested_groups),
            "paths": sorted(requested_paths),
            "downloaded": downloaded,
            "manifest": str(MANIFEST_PATH.name),
        }
    except Exception as exc:  # pragma: no cover - cloud credential/runtime dependent
        LOGGER.exception("Cloud asset bootstrap failed")
        return {"enabled": True, "bucket": bucket_name, "downloaded": [], "error": str(exc)}
