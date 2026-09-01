from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .config import MODEL_ROOT, PROJECT_ROOT


RELEASE_MANIFEST_PATH = PROJECT_ROOT / "configs" / "release_manifest.json"
MODEL_REGISTRY_PATH = PROJECT_ROOT / "configs" / "model_registry.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_release_manifest(path: Path | None = None) -> dict[str, Any]:
    target = path or RELEASE_MANIFEST_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def _record(
    checks: list[dict[str, Any]],
    name: str,
    expected: Any,
    actual: Any,
) -> None:
    checks.append(
        {
            "name": name,
            "status": "pass" if actual == expected else "fail",
            "expected": expected,
            "actual": actual,
        }
    )


def verify_release(
    config: dict[str, Any],
    *,
    manifest_path: Path | None = None,
    registry_path: Path | None = None,
    model_root: Path | None = None,
    verify_hashes: bool = True,
) -> dict[str, Any]:
    """Verify that configuration, registry and model bytes describe one release."""

    manifest = load_release_manifest(manifest_path)
    registry_target = registry_path or MODEL_REGISTRY_PATH
    registry = json.loads(registry_target.read_text(encoding="utf-8"))
    models = model_root or MODEL_ROOT
    profiles = manifest["active_profiles"]
    contract = manifest["runtime_contract"]
    inference = config["inference"]
    checks: list[dict[str, Any]] = []

    _record(checks, "config.object_profile", profiles["object"], inference.get("object_profile"))
    _record(checks, "config.lane_profile", profiles["lane"], inference.get("lane_profile"))
    _record(
        checks,
        "registry.active_object_profile",
        profiles["object"],
        registry.get("active_object_profile"),
    )
    _record(
        checks,
        "registry.active_traffic_sign_profile",
        profiles["traffic_sign"],
        registry.get("active_traffic_sign_profile"),
    )

    object_profile = inference.get("object_profiles", {}).get(profiles["object"], {})
    runtime_values = {
        "object_model": object_profile.get("model"),
        "object_onnx_model": object_profile.get("onnx_model"),
        "sign_model": inference.get("sign_model"),
        "sign_onnx_model": inference.get("sign_onnx_model"),
        "speed_classifier_model": inference.get("speed_classifier_model"),
        # YOLOP currently has a fixed path in the perception engine.
        "lane_model": "yolop_lane_detection_640.onnx"
        if inference.get("lane_profile") == "yolop"
        else None,
    }
    for key, expected in contract.items():
        _record(checks, f"runtime.{key}", expected, runtime_values.get(key))

    for artifact in manifest["artifacts"]:
        path = models / artifact["file"]
        exists = path.is_file()
        _record(checks, f"artifact.{artifact['component']}.exists", True, exists)
        if exists and verify_hashes:
            _record(
                checks,
                f"artifact.{artifact['component']}.sha256",
                artifact["sha256"].upper(),
                _sha256(path),
            )

    failed = [item for item in checks if item["status"] == "fail"]
    return {
        "status": "pass" if not failed else "fail",
        "release_id": manifest["release_id"],
        "release_level": manifest["release_level"],
        "checks_total": len(checks),
        "checks_failed": len(failed),
        "checks": checks,
    }
