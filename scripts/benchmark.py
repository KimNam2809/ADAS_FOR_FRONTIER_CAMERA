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
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
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
    parser.add_argument("--object-profile", default="baseline_coco")
    parser.add_argument("--lane-profile", choices=["yolop", "ufldv2_fusion"], default="yolop")
    parser.add_argument(
        "--traffic-context-mode",
        choices=["off", "shadow", "enforce"],
        default=os.getenv("ROADWATCH_TRAFFIC_CONTEXT_MODE", "off"),
    )
    args = parser.parse_args()

    # ConfigManager reads this at construction time.  Keeping it on the
    # benchmark command makes off/enforce comparisons reproducible.
    os.environ["ROADWATCH_TRAFFIC_CONTEXT_MODE"] = args.traffic_context_mode

    stamp = int(time.time() * 1000)
    config = ConfigManager(
        runtime_path=PROJECT_ROOT / "reports" / f"benchmark-runtime-{stamp}.json"
    )
    config.update(
        {
            "inference": {
                "object_profile": args.object_profile,
                "lane_profile": args.lane_profile,
            },
            "audio": {"enabled": False},
        },
        persist=False,
    )
    storage = Storage(PROJECT_ROOT / "reports" / f"benchmark-events-{stamp}.db")
    service = RoadWatchService(config, storage)
    try:
        service.start(args.source)
        # Measure the requested replay window after model warmup so a slow
        # first graph initialization cannot silently consume the benchmark
        # window and under-report steady-state FPS.
        warmup_deadline = time.time() + 180.0
        while time.time() < warmup_deadline and service.is_running:
            current = service.status()
            if current.get("stage") == "inference":
                break
            time.sleep(0.1)
        deadline = time.time() + max(5, args.seconds)
        context_samples: list[dict] = []
        while time.time() < deadline and service.is_running:
            context_samples.append(dict(service.status().get("traffic_context", {})))
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
        "profiles": {
            "object": args.object_profile,
            "lane": args.lane_profile,
        },
        "metrics": status["metrics"],
        "models": status.get("models", {}),
        "lane": status.get("lane", {}),
        "traffic_context": status.get("traffic_context", {}),
        "traffic_context_peak": {
            "mode": "dense" if any(item.get("mode") == "dense" for item in context_samples) else "normal",
            "max_density_score": round(max((float(item.get("density_score", 0.0)) for item in context_samples), default=0.0), 4),
            "max_confirmed_road_users": max((int(item.get("confirmed_road_users", 0)) for item in context_samples), default=0),
            "max_two_wheeler_count": max((int(item.get("two_wheeler_count", 0)) for item in context_samples), default=0),
            "transitions": [item.get("transition") for item in context_samples if item.get("transition")],
        },
        "event_count": len(status.get("events", [])),
        "event_routes": {
            str(event.get("audio_route") or event.get("audio_action") or "unknown"): sum(
                1 for item in status.get("events", [])
                if str(item.get("audio_route") or item.get("audio_action") or "unknown")
                == str(event.get("audio_route") or event.get("audio_action") or "unknown")
            )
            for event in status.get("events", [])
        },
        "degraded_reasons": status.get("degraded_reasons", []),
        "pipeline_error": status.get("error"),
        "measurement_note": "Replay benchmark; image-space risk is not metric TTC.",
    }
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nĐã lưu bằng chứng benchmark: {output}")
    return 0 if not report["degraded_reasons"] and not report["pipeline_error"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
