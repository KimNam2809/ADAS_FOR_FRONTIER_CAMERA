from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.config import ConfigManager, model_inventory  # noqa: E402


def main() -> int:
    config = ConfigManager().snapshot()
    try:
        import onnxruntime as ort

        providers = ort.get_available_providers()
    except Exception as exc:
        providers = [f"unavailable: {exc}"]
    calibration_path = PROJECT_ROOT / "configs" / "camera_calibration.json"
    calibration = (
        json.loads(calibration_path.read_text(encoding="utf-8"))
        if calibration_path.exists()
        else {"calibrated": False, "reason": "camera_calibration.json chưa tồn tại"}
    )
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "onnxruntime_providers": providers,
        "models": model_inventory(),
        "deployment_files": {
            name: (PROJECT_ROOT / name).exists()
            for name in (
                "Dockerfile",
                "Dockerfile.nvidia",
                "Dockerfile.jetson",
                "docker-compose.yml",
                "docker-compose.nvidia.yml",
            )
        },
        "camera_calibration": calibration,
        "vehicle_io": {
            "configured_read_only": bool(config["vehicle"].get("can_read_only", True)),
            "actuator_api": False,
            "validated_on_vehicle": False,
        },
        "gates": {
            "metric_ttc_allowed": bool(calibration.get("calibrated", False)),
            "jetson_validated": False,
            "closed_course_validated": False,
        },
    }
    output = PROJECT_ROOT / "reports" / "edge-preflight-latest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
