from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from .config import MEDIA_ROOT, MODEL_ROOT, PROJECT_ROOT


LOGGER = logging.getLogger(__name__)
MANIFEST_PATH = PROJECT_ROOT / "configs" / "cloud_assets.json"


def _download_if_missing(bucket_name: str, item: dict[str, Any], root: Path, client: Any) -> str:
    relative = Path(str(item["path"]))
    target = (root / relative).resolve()
    if root.resolve() not in target.parents:
        raise ValueError(f"Cloud asset path vượt root: {relative}")
    if target.exists() and target.stat().st_size > 0:
        return f"local:{target.name}"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.download")
    blob = client.bucket(bucket_name).blob(str(item["object"]))
    if not blob.exists(client):
        raise FileNotFoundError(f"Không tìm thấy GCS asset: gs://{bucket_name}/{item['object']}")
    blob.download_to_filename(str(temporary))
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
        for item in manifest.get("models", []):
            downloaded.append(_download_if_missing(bucket_name, item, MODEL_ROOT, client))
        for item in manifest.get("media", []):
            downloaded.append(_download_if_missing(bucket_name, item, MEDIA_ROOT, client))
        return {
            "enabled": True,
            "bucket": bucket_name,
            "downloaded": downloaded,
            "manifest": str(MANIFEST_PATH.name),
        }
    except Exception as exc:  # pragma: no cover - cloud credential/runtime dependent
        LOGGER.exception("Cloud asset bootstrap failed")
        return {"enabled": True, "bucket": bucket_name, "downloaded": [], "error": str(exc)}
