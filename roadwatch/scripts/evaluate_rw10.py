from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from roadwatch.lane_gate import evaluate_lane_annotations  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RW-10 annotation/model evidence")
    parser.add_argument("--queue", type=Path, default=ROOT / "evaluation/rw10_lane_annotation_queue.json")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/rw10_quality_gate.json")
    args = parser.parse_args()
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    report = {
        "schema_version": 1,
        "task_id": "RW-10",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **evaluate_lane_annotations(queue.get("records", [])),
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
