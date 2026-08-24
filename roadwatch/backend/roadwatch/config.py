from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "default.json"
RUNTIME_CONFIG_PATH = PROJECT_ROOT / "configs" / "runtime.json"
MEDIA_ROOT = PROJECT_ROOT / "media"
MODEL_ROOT = PROJECT_ROOT / "models"
DATA_ROOT = PROJECT_ROOT / "data"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


class ConfigManager:
    """Thread-safe configuration with a checked, local runtime override."""

    MUTABLE_SECTIONS = {"app", "inference", "tracking", "risk", "alerts", "audio", "vehicle"}

    def __init__(self, runtime_path: Path | None = None) -> None:
        self.runtime_path = runtime_path or RUNTIME_CONFIG_PATH
        self._lock = threading.RLock()
        self._config = self._load()

    def _load(self) -> dict[str, Any]:
        base = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
        if self.runtime_path.exists():
            override = json.loads(self.runtime_path.read_text(encoding="utf-8"))
            base = _deep_merge(base, override)

        source = os.getenv("ROADWATCH_SOURCE")
        if source:
            base["app"]["default_source"] = source
        if os.getenv("ROADWATCH_DISABLE_AUDIO", "0") == "1":
            base["audio"]["enabled"] = False
        if os.getenv("ROADWATCH_DEVICE"):
            base["inference"]["device"] = os.environ["ROADWATCH_DEVICE"]
        if os.getenv("ROADWATCH_RUNTIME"):
            base["inference"]["runtime"] = os.environ["ROADWATCH_RUNTIME"]
        if os.getenv("ROADWATCH_OBJECT_PROFILE"):
            base["inference"]["object_profile"] = os.environ["ROADWATCH_OBJECT_PROFILE"]
        if os.getenv("ROADWATCH_LANE_PROFILE"):
            base["inference"]["lane_profile"] = os.environ["ROADWATCH_LANE_PROFILE"]
        if os.getenv("ROADWATCH_MAX_FPS"):
            base["app"]["max_processed_fps"] = float(os.environ["ROADWATCH_MAX_FPS"])
        return base

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._config)

    def update(self, patch: dict[str, Any], persist: bool = True) -> dict[str, Any]:
        unknown = set(patch) - self.MUTABLE_SECTIONS
        if unknown:
            raise ValueError(f"Không được phép sửa các mục: {', '.join(sorted(unknown))}")
        candidate = _deep_merge(self.snapshot(), patch)
        self._validate(candidate)
        with self._lock:
            self._config = candidate
            if persist:
                self.runtime_path.parent.mkdir(parents=True, exist_ok=True)
                persisted = {
                    key: copy.deepcopy(candidate[key])
                    for key in self.MUTABLE_SECTIONS
                    if key in candidate
                }
                self.runtime_path.write_text(
                    json.dumps(persisted, ensure_ascii=False, indent=2), encoding="utf-8"
                )
        return self.snapshot()

    @staticmethod
    def _validate(config: dict[str, Any]) -> None:
        inf = config["inference"]
        if not 0.05 <= float(inf["object_confidence"]) <= 0.99:
            raise ValueError("object_confidence phải nằm trong [0.05, 0.99]")
        if not 0.05 <= float(inf["sign_confidence"]) <= 0.99:
            raise ValueError("sign_confidence phải nằm trong [0.05, 0.99]")
        if int(inf["image_size"]) not in {320, 416, 512, 640, 768}:
            raise ValueError("image_size không thuộc profile được kiểm thử")
        object_profile = str(inf.get("object_profile", "baseline_coco"))
        if object_profile not in inf.get("object_profiles", {}):
            raise ValueError(f"Object detector profile không tồn tại: {object_profile}")
        if str(inf.get("lane_profile", "yolop")) not in {"yolop", "ufldv2_fusion"}:
            raise ValueError("Lane profile không được hỗ trợ")
        risk = config["risk"]
        if float(risk["fcw_warning"]) >= float(risk["fcw_critical"]):
            raise ValueError("Ngưỡng FCW warning phải nhỏ hơn critical")
        if config["vehicle"]["profile"] not in config["vehicle"]["profiles"]:
            raise ValueError("Vehicle profile không tồn tại")

    @staticmethod
    def model_path(name: str) -> Path:
        path = (MODEL_ROOT / name).resolve()
        if not _is_inside(path, MODEL_ROOT):
            raise ValueError("Model path không hợp lệ")
        return path

    @staticmethod
    def media_source(value: str | int) -> str | int:
        if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
            return int(value)
        path = Path(value)
        if not path.is_absolute():
            path = MEDIA_ROOT / path
        path = path.resolve()
        if not _is_inside(path, MEDIA_ROOT):
            raise ValueError("Video phải nằm trong roadwatch/media")
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy nguồn video: {path.name}")
        return str(path)


def model_inventory() -> list[dict[str, Any]]:
    inventory = [
        ("yolo11n.pt", True),
        ("roadwatch_objects_v1.pt", False),
        ("roadwatch_objects_v1_1.pt", False),
        ("roadwatch_objects_v2.pt", False),
        ("roadwatch_objects_v2.onnx", False),
        ("yolo11s_vietnam_traffic.pt", True),
        ("roadwatch_detector_v2.pt", False),
        ("roadwatch_detector_v2.onnx", False),
        ("yolop_lane_detection_640.onnx", True),
        ("yolop_lane_detection.pth", False),
        ("ufldv2_culane_res18_320x1600.onnx", False),
        ("roadwatch_speed_digits_v2.pt", False),
        ("roadwatch_speed_digits_v2.onnx", False),
    ]
    return [
        {
            "name": name,
            "required": required,
            "available": (MODEL_ROOT / name).exists(),
            "size_mb": round((MODEL_ROOT / name).stat().st_size / 1_048_576, 2)
            if (MODEL_ROOT / name).exists()
            else 0,
        }
        for name, required in inventory
    ]


def media_inventory() -> list[dict[str, Any]]:
    supported = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    return [
        {"name": item.name, "size_mb": round(item.stat().st_size / 1_048_576, 2)}
        for item in sorted(MEDIA_ROOT.glob("*"))
        if item.is_file() and item.suffix.lower() in supported
    ]
