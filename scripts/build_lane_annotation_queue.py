from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = [
    ("dashcam_vietnam_night.mp4", "reports/review/rw05_night", 100, ["night"]),
    ("dashcam_vietnam_rain+night.mp4", "reports/review/rw05_rain_night", 100, ["night", "rain"]),
    ("dashcam_vietnam_traffic_multi.mp4", "reports/review/rw05_traffic_multi", 200, ["day", "dense_traffic"]),
]


def evenly_select(rows: list[dict], count: int) -> list[dict]:
    if len(rows) <= count:
        return rows
    return [rows[round(index * (len(rows) - 1) / (count - 1))] for index in range(count)]


def build() -> dict:
    records: list[dict] = []
    for source, report_root, count, conditions in DEFAULT_SOURCES:
        root = ROOT / report_root
        with (root / "selected_frames.csv").open("r", encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        inventory = json.loads((root / "inventory.json").read_text(encoding="utf-8"))
        for row in evenly_select(rows, count):
            records.append(
                {
                    "id": f"{Path(source).stem}-{int(row['selection_id']):04d}",
                    "source": source,
                    "source_sha256": inventory["sha256"],
                    "timestamp_s": float(row["timestamp_s"]),
                    "image": f"{report_root}/{row['file']}",
                    "conditions": conditions,
                    "ground_truth_lane_count": None,
                    "ego_left_boundary": [],
                    "ego_right_boundary": [],
                    "uncertain": None,
                    "review_status": "pending",
                    "predicted_lane_count": None,
                    "ego_boundary_f1": None,
                    "ldw_false_alerts": 0,
                    "measured_seconds": 0,
                }
            )
    return {
        "schema_version": 1,
        "task_id": "RW-10",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "split_policy": "video-grouped; these source videos are evaluation/annotation only",
        "annotation_instruction": (
            "Count visible same-direction lane instances; mark ego left/right polylines; "
            "use uncertain=true when boundaries are not defensible."
        ),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build RW-10 lane annotation queue")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/rw10_lane_annotation_queue.json")
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(payload["records"]), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
