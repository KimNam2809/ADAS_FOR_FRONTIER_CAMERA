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
VOICE_ROOT = PROJECT_ROOT / "voices"


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

    MUTABLE_SECTIONS = {
        "app",
        "inference",
        "tracking",
        "risk",
        "alerts",
        "audio",
        "vehicle",
        "traffic_context",
        "slm",
    }

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
        if os.getenv("ROADWATCH_AUDIO_OUTPUT"):
            base["audio"]["output_owner"] = os.environ["ROADWATCH_AUDIO_OUTPUT"]
        elif os.getenv("ROADWATCH_CLOUD_MODE"):
            # Cloud Web has no user-facing speaker. The authenticated browser
            # is the sole playback owner, even when server audio is disabled.
            base["audio"]["output_owner"] = "browser"
        if os.getenv("ROADWATCH_TTS_PROVIDER"):
            base["audio"]["provider"] = os.environ["ROADWATCH_TTS_PROVIDER"].strip().lower()
        if os.getenv("ROADWATCH_TTS_VOICE"):
            base["audio"]["piper_voice"] = os.environ["ROADWATCH_TTS_VOICE"]
        if os.getenv("ROADWATCH_TTS_VOICE_NAME"):
            base["audio"]["piper_voice_name"] = os.environ["ROADWATCH_TTS_VOICE_NAME"]
        if os.getenv("ROADWATCH_DEVICE"):
            base["inference"]["device"] = os.environ["ROADWATCH_DEVICE"]
        if os.getenv("ROADWATCH_RUNTIME"):
            base["inference"]["runtime"] = os.environ["ROADWATCH_RUNTIME"]
        if os.getenv("ROADWATCH_OBJECT_PROFILE"):
            base["inference"]["object_profile"] = os.environ["ROADWATCH_OBJECT_PROFILE"]
        if os.getenv("ROADWATCH_LANE_PROFILE"):
            base["inference"]["lane_profile"] = os.environ["ROADWATCH_LANE_PROFILE"]
        if os.getenv("ROADWATCH_TWINLITENETPLUS_MODEL"):
            base["inference"]["twinlitenetplus_model"] = os.environ[
                "ROADWATCH_TWINLITENETPLUS_MODEL"
            ]
        if os.getenv("ROADWATCH_MAX_FPS"):
            base["app"]["max_processed_fps"] = float(os.environ["ROADWATCH_MAX_FPS"])
        if os.getenv("ROADWATCH_STREAM_FPS"):
            base["app"]["stream_fps"] = float(os.environ["ROADWATCH_STREAM_FPS"])
        if os.getenv("ROADWATCH_STREAM_JPEG_QUALITY"):
            base["app"]["stream_jpeg_quality"] = int(
                os.environ["ROADWATCH_STREAM_JPEG_QUALITY"]
            )
        if os.getenv("ROADWATCH_STREAM_MAX_WIDTH"):
            base["app"]["stream_max_width"] = int(
                os.environ["ROADWATCH_STREAM_MAX_WIDTH"]
            )
        if os.getenv("ROADWATCH_PUBLISH_SKIPPED_FRAMES"):
            base["app"]["publish_skipped_frames"] = os.environ[
                "ROADWATCH_PUBLISH_SKIPPED_FRAMES"
            ].lower() in {"1", "true", "yes", "on"}
        if os.getenv("ROADWATCH_ASYNC_OPTIONAL"):
            base["inference"]["async_optional_perception"] = os.environ[
                "ROADWATCH_ASYNC_OPTIONAL"
            ].lower() in {"1", "true", "yes", "on"}
        if os.getenv("ROADWATCH_TRAFFIC_CONTEXT_MODE"):
            requested_context_mode = os.environ["ROADWATCH_TRAFFIC_CONTEXT_MODE"].strip().lower()
            if requested_context_mode in {"off", "shadow", "enforce"}:
                base.setdefault("traffic_context", {})["mode"] = requested_context_mode
        if os.getenv("ROADWATCH_SLM_ENABLED") is not None:
            base.setdefault("slm", {})["enabled"] = os.getenv("ROADWATCH_SLM_ENABLED", "0") == "1"
        if os.getenv("ROADWATCH_SLM_MODEL_DIR"):
            base.setdefault("slm", {})["model_dir"] = os.environ["ROADWATCH_SLM_MODEL_DIR"]
        if os.getenv("ROADWATCH_SLM_DEVICE"):
            base.setdefault("slm", {})["device"] = os.environ["ROADWATCH_SLM_DEVICE"]
        if os.getenv("ROADWATCH_SLM_MAX_NEW_TOKENS"):
            base.setdefault("slm", {})["max_new_tokens"] = int(os.environ["ROADWATCH_SLM_MAX_NEW_TOKENS"])
        if os.getenv("ROADWATCH_SLM_QUEUE_SIZE"):
            base.setdefault("slm", {})["queue_size"] = int(os.environ["ROADWATCH_SLM_QUEUE_SIZE"])
        if os.getenv("ROADWATCH_CLOUD_MODE"):
            # Cloud Run is an evaluation/replay plane. Keep the deterministic
            # edge profile untouched while avoiding a PyTorch classifier cold
            # start in the public CPU service.
            base["inference"]["device"] = "cpu"
            base["inference"]["runtime"] = "cpu"
            base["inference"]["prefer_onnx_detectors"] = True
            base["app"]["max_processed_fps"] = min(
                float(base["app"].get("max_processed_fps", 12.0)), 6.0
            )
            if os.getenv("ROADWATCH_CLOUD_IMAGE_SIZE"):
                base["inference"]["image_size"] = int(os.environ["ROADWATCH_CLOUD_IMAGE_SIZE"])
            cloud_full = os.getenv("ROADWATCH_CLOUD_FULL", "0") == "1"
            if cloud_full:
                # Keep object inference at 320 while fixed-shape ONNX heads read
                # their own input dimensions. Optional heads publish a bounded,
                # session-scoped cache so they never block the object/risk loop.
                base["inference"]["enable_lane"] = True
                base["inference"]["enable_signs"] = True
                base["inference"]["object_onnx_model"] = "yolo11n_320.onnx"
                base["inference"]["object_profiles"]["baseline_coco"]["onnx_model"] = "yolo11n_320.onnx"
                base["inference"]["sign_onnx_model"] = "roadwatch_detector_v2_416.onnx"
                base["inference"]["speed_classifier_model"] = "roadwatch_speed_digits_v2.onnx"
                base["inference"]["lane_profile"] = "yolop"
                base["inference"]["object_interval"] = 1
                base["inference"]["sign_interval"] = 1
                base["inference"]["sign_candidate_interval"] = 1
                base["inference"]["lane_interval"] = 4
                base["inference"]["async_optional_perception"] = True
                base["inference"]["optional_max_staleness_seconds"] = 1.5
                base["app"]["max_processed_fps"] = min(
                    float(base["app"].get("max_processed_fps", 6.0)), 4.0
                )
            else:
                base["inference"]["speed_classifier_model"] = "__cloud_speed_classifier_disabled__.pt"
            if os.getenv("ROADWATCH_CLOUD_FAST", "0") == "1" and not cloud_full:
                # Cloud Run is a public replay/evaluation plane, not the edge
                # safety path. On CPU, YOLOP and the sign model can monopolize
                # a container for minutes on the first frame. Keep a useful
                # object-only preview and leave full perception to local/AAOS.
                base["inference"]["enable_lane"] = False
                base["inference"]["enable_signs"] = False
                base["inference"]["object_onnx_model"] = "yolo11n_320.onnx"
                base["inference"]["object_model"] = "yolo11n.pt"
                base["inference"]["object_profiles"]["baseline_coco"]["onnx_model"] = "yolo11n_320.onnx"
                base["inference"]["object_interval"] = 1
                base["inference"]["lane_interval"] = 999999
                base["inference"]["sign_interval"] = 999999
                base["app"]["max_processed_fps"] = min(
                    float(base["app"].get("max_processed_fps", 6.0)), 4.0
                )
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
        app = config["app"]
        if not 1.0 <= float(app.get("stream_fps", 30.0)) <= 60.0:
            raise ValueError("stream_fps phải nằm trong [1, 60]")
        if not 35 <= int(app.get("stream_jpeg_quality", 72)) <= 95:
            raise ValueError("stream_jpeg_quality phải nằm trong [35, 95]")
        if not 320 <= int(app.get("stream_max_width", 1280)) <= 3840:
            raise ValueError("stream_max_width phải nằm trong [320, 3840]")
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
        if str(inf.get("lane_profile", "yolop")) not in {
            "yolop",
            "ufldv2_fusion",
            "twinlitenetplus",
        }:
            raise ValueError("Lane profile không được hỗ trợ")
        risk = config["risk"]
        if float(risk["fcw_warning"]) >= float(risk["fcw_critical"]):
            raise ValueError("Ngưỡng FCW warning phải nhỏ hơn critical")
        if config["vehicle"]["profile"] not in config["vehicle"]["profiles"]:
            raise ValueError("Vehicle profile không tồn tại")
        context_mode = str(config.get("traffic_context", {}).get("mode", "off")).lower()
        if context_mode not in {"off", "shadow", "enforce"}:
            raise ValueError("traffic_context.mode phải là off, shadow hoặc enforce")
        slm = config.get("slm", {})
        if not 16 <= int(slm.get("max_new_tokens", 128)) <= 192:
            raise ValueError("slm.max_new_tokens phải nằm trong [16, 192]")
        if not 1 <= int(slm.get("queue_size", 8)) <= 64:
            raise ValueError("slm.queue_size phải nằm trong [1, 64]")

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
        ("yolo26n.pt", False),
        ("yolo26n.onnx", False),
        ("yolo26s.pt", False),
        ("yolo26s.onnx", False),
        ("roadwatch_objects_v1.pt", False),
        ("roadwatch_objects_v1_1.pt", False),
        ("roadwatch_objects_v2.pt", False),
        ("roadwatch_objects_v2.onnx", False),
        ("yolo11s_vietnam_traffic.pt", True),
        ("roadwatch_detector_v2.pt", False),
        ("roadwatch_detector_v2.onnx", False),
        ("roadwatch_detector_v2_416.onnx", False),
        ("yolop_lane_detection_640.onnx", True),
        ("yolop_lane_detection.pth", False),
        ("twinlitenetplus_medium.onnx", False),
        ("twinlitenetplus_medium.pth", False),
        ("ufldv2_culane_res18_320x1600.onnx", False),
        ("roadwatch_speed_digits_v2.pt", False),
        ("roadwatch_speed_digits_v2.onnx", False),
        ("qwen2.5-0.5b/onnx/model_q4f16.onnx", False),
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
