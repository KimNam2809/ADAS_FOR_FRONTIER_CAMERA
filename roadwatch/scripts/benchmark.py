from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
os.environ.setdefault("ROADWATCH_DISABLE_AUDIO", "1")

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.pipeline import RoadWatchService  # noqa: E402
from roadwatch.storage import Storage  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark RoadWatch trên video local")
    parser.add_argument("--source", default="test_video10.mp4")
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--output", default="reports/benchmark-latest.json")
    args = parser.parse_args()

    config = ConfigManager()
    storage = Storage()
    service = RoadWatchService(config, storage)
    try:
        service.start(args.source)
        deadline = time.time() + max(5, args.seconds)
        while time.time() < deadline and service.is_running:
            time.sleep(0.5)
        status = service.status()
    finally:
        service.close()
        storage.close()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
        },
        "source": args.source,
        "duration_seconds": args.seconds,
        "metrics": status["metrics"],
        "models": status.get("models", {}),
        "lane": status.get("lane", {}),
        "event_count": len(status.get("events", [])),
        "degraded_reasons": status.get("degraded_reasons", []),
        "measurement_note": "Replay benchmark; image-space risk is not metric TTC.",
    }
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nĐã lưu bằng chứng benchmark: {output}")
    return 0 if not report["degraded_reasons"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
