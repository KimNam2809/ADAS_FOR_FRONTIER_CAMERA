from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["ROADWATCH_DISABLE_AUDIO"] = "1"

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.pipeline import RoadWatchService  # noqa: E402
from roadwatch.storage import Storage  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture per-frame RoadWatch evidence")
    parser.add_argument("source")
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    runtime = ROOT / "reports" / "runtime-real-world-trace.json"
    database = ROOT / "reports" / "events-real-world-trace.db"
    config = ConfigManager(runtime_path=runtime)
    config.update(
        {
            "app": {"loop_video": False, "pace_replay": True, "max_processed_fps": 6.0},
            "audio": {"enabled": False},
        },
        persist=False,
    )
    storage = Storage(database)
    service = RoadWatchService(config, storage)
    frames: list[dict] = []
    last_frame = -1
    try:
        service.start(args.source, args.start, args.duration)
        while service.is_running:
            status = service.status()
            frame_id = int(status.get("frame_id", 0))
            if frame_id != last_frame:
                frames.append(
                    {
                        "frame_id": frame_id,
                        "source_time": status.get("source_time"),
                        "lane": status.get("lane"),
                        "tracks": status.get("tracks", []),
                        "signs": status.get("signs", []),
                        "sign_trace": status.get("sign_trace", []),
                        "active_events": status.get("active_events", []),
                    }
                )
                last_frame = frame_id
            time.sleep(0.02)
    finally:
        service.close()
        storage.close()
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"source": args.source, "frames": frames}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "frames": len(frames)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
