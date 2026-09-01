from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from roadwatch.calibration import load_valid_calibration  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a RoadWatch camera calibration")
    parser.add_argument("--calibration", type=Path, default=ROOT / "configs/camera_calibration.json")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/rw07_calibration_gate.json")
    args = parser.parse_args()
    artifact, errors = load_valid_calibration(args.calibration)
    payload = {
        "schema_version": 1,
        "task_id": "RW-07",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "blocked",
        "calibration_path": str(args.calibration),
        "camera_id": artifact.get("camera_id"),
        "metric_ttc_alerting_allowed": False,
        "errors": errors,
        "next_gate": "measured day/night closed-course distance and TTC evaluation",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
