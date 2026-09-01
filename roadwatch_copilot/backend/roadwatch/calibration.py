from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalize_calibration(payload: dict[str, Any]) -> dict[str, Any]:
    image_size = payload.get("image_size") or [
        payload.get("image_width"),
        payload.get("image_height"),
    ]
    intrinsics = payload.get("intrinsics") or {}
    return {
        **payload,
        "image_size": image_size,
        "fx": payload.get("fx", intrinsics.get("fx")),
        "fy": payload.get("fy", intrinsics.get("fy")),
        "cx": payload.get("cx", intrinsics.get("cx")),
        "cy": payload.get("cy", intrinsics.get("cy")),
    }


def validate_calibration(payload: dict[str, Any]) -> list[str]:
    item = normalize_calibration(payload)
    errors: list[str] = []
    if int(item.get("schema_version", 0)) != 1:
        errors.append("schema_version must be 1")
    if not bool(item.get("calibrated")):
        errors.append("calibrated must be true")
    if not str(item.get("camera_id") or "").strip():
        errors.append("camera_id is required")
    image_size = item.get("image_size") or []
    if len(image_size) != 2 or any(float(value or 0) <= 0 for value in image_size):
        errors.append("positive image_size [width, height] is required")
    for key in ("fx", "fy"):
        if float(item.get(key) or 0) <= 0:
            errors.append(f"{key} must be positive")
    if len(item.get("distortion_coefficients") or []) < 4:
        errors.append("at least four distortion coefficients are required")
    count = int(item.get("valid_image_count", 0))
    if count < 12:
        errors.append("valid_image_count must be at least 12")
    rms = float(item.get("rms_reprojection_error", 99.0))
    if not 0 <= rms < 1.0:
        errors.append("rms_reprojection_error must be below 1.0 px")
    hashes = item.get("source_image_sha256") or []
    if len(hashes) != count or any(len(str(value)) != 64 for value in hashes):
        errors.append("source_image_sha256 must contain one SHA-256 per valid image")
    if bool(item.get("quality_gate", {}).get("metric_ttc_alerting_allowed", False)):
        errors.append("calibration alone must not enable metric TTC alerting")
    return errors


def load_valid_calibration(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, ["calibration artifact does not exist"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"invalid calibration JSON: {exc}"]
    errors = validate_calibration(payload)
    return normalize_calibration(payload), errors
