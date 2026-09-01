from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import MEDIA_ROOT


def _bucket_name() -> str:
    return os.getenv("ROADWATCH_GCS_ASSET_BUCKET", "").strip()


def _client() -> Any:
    from google.cloud import storage

    return storage.Client()


def _media_path(source: str) -> Path:
    target = (MEDIA_ROOT / source).resolve()
    try:
        target.relative_to(MEDIA_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Nguồn video không nằm trong media root") from exc
    return target


def persist_uploaded_media(source: str) -> dict[str, Any]:
    """Persist an uploaded local adapter file to GCS when cloud mode is active."""
    bucket_name = _bucket_name()
    path = _media_path(source)
    if not bucket_name:
        return {"storage_mode": "local_ephemeral", "durable": False}
    blob_name = f"media/{Path(source).as_posix()}"
    blob = _client().bucket(bucket_name).blob(blob_name)
    blob.upload_from_filename(str(path), content_type="video/mp4")
    return {
        "storage_mode": "gcs",
        "durable": True,
        "storage_uri": f"gs://{bucket_name}/{blob_name}",
    }


def materialize_media_source(source: str) -> dict[str, Any]:
    """Ensure a library/upload source exists on the current Cloud Run instance."""
    path = _media_path(source)
    if path.exists() and path.stat().st_size > 0:
        return {"available": True, "source": source, "storage_mode": "local"}
    bucket_name = _bucket_name()
    if not bucket_name:
        return {"available": False, "source": source, "storage_mode": "unconfigured"}
    blob_name = f"media/{Path(source).as_posix()}"
    client = _client()
    blob = client.bucket(bucket_name).blob(blob_name)
    if not blob.exists(client):
        return {"available": False, "source": source, "storage_mode": "gcs_missing"}
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.download")
    blob.download_to_filename(str(temporary))
    temporary.replace(path)
    return {"available": True, "source": source, "storage_mode": "gcs"}
