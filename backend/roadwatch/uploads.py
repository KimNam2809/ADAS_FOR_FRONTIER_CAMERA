from __future__ import annotations

import hashlib
import os
import re
import uuid
from pathlib import Path
from typing import Any

import cv2
from fastapi import UploadFile

from .catalog import SUPPORTED_VIDEO_EXTENSIONS, _probe_video
from .config import MEDIA_ROOT


def _max_upload_bytes() -> int:
    value = os.getenv("ROADWATCH_MAX_UPLOAD_MB", "512")
    try:
        megabytes = max(1, min(int(value), 2048))
    except ValueError:
        megabytes = 512
    return megabytes * 1_048_576


def _safe_filename(filename: str | None) -> str:
    original = Path(filename or "upload.mp4").name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(original).stem).strip("._") or "upload"
    suffix = Path(original).suffix.lower()
    if suffix not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError("Chỉ hỗ trợ video MP4, AVI, MOV, MKV hoặc WEBM")
    return f"{stem[:96]}{suffix}"


def save_upload(upload: UploadFile) -> dict[str, Any]:
    """Store a user video below media/uploads and return a replay-safe source.

    The local adapter is intentionally atomic and bounded. Cloud deployment
    should use a signed GCS upload and keep this endpoint disabled for large
    public traffic; the returned contract remains the same.
    """
    filename = _safe_filename(upload.filename)
    run_id = str(uuid.uuid4())
    target_dir = (MEDIA_ROOT / "uploads" / run_id).resolve()
    target_dir.mkdir(parents=True, exist_ok=False)
    temporary = target_dir / f".{filename}.part"
    target = target_dir / filename
    digest = hashlib.sha256()
    total = 0
    try:
        with temporary.open("wb") as destination:
            while True:
                chunk = upload.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > _max_upload_bytes():
                    raise ValueError(
                        f"Video vượt giới hạn {_max_upload_bytes() // 1_048_576} MB"
                    )
                digest.update(chunk)
                destination.write(chunk)
        temporary.replace(target)
        probe = _probe_video(target)
        if not cv2.haveImageReader(str(target)) and probe["frame_count"] <= 0:
            raise ValueError("File không phải video hợp lệ hoặc codec không được hỗ trợ")
        relative = target.relative_to(MEDIA_ROOT.resolve()).as_posix()
        return {
            "run_id": run_id,
            "name": target.name,
            "source": relative,
            "relative_source": relative,
            "source_kind": "upload",
            "size_mb": round(total / 1_048_576, 2),
            "sha256": digest.hexdigest(),
            **probe,
        }
    except Exception:
        if temporary.exists():
            temporary.unlink()
        if target.exists():
            target.unlink()
        if target_dir.exists() and not any(target_dir.iterdir()):
            target_dir.rmdir()
        raise
    finally:
        upload.file.close()
