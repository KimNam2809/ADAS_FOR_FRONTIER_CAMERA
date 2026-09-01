from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVENT_TYPES = [
    "fcw",
    "vulnerable_road_user",
    "cut_in",
    "cross_traffic",
    "lane_departure",
    "lead_vehicle_braking",
    "speed_sign",
    "traffic_sign",
    "fallen_rider",
]


def choose_windows(
    samples: list[dict],
    duration: float,
    count: int,
    window_seconds: float,
    window_prefix: str = "dashcam-vn",
) -> list[dict]:
    if count <= 0 or duration < window_seconds:
        return []
    # Never count overlapping windows as independent exhaustive coverage.
    count = min(count, max(1, int(duration // window_seconds)))
    bin_width = duration / count
    windows: list[dict] = []
    for index in range(count):
        bin_start = index * bin_width
        bin_end = min(duration, (index + 1) * bin_width)
        candidates = [
            item for item in samples if bin_start <= float(item["timestamp_s"]) < bin_end
        ]
        if candidates:
            center_item = max(
                candidates,
                key=lambda item: (
                    float(item.get("scene_delta", 0)),
                    float(item.get("quality_score", 0)),
                ),
            )
            center = float(center_item["timestamp_s"])
        else:
            center_item = {}
            center = (bin_start + bin_end) / 2
        start = max(bin_start, min(center - window_seconds / 2, bin_end - window_seconds))
        end = start + window_seconds
        windows.append(
            {
                "window_id": f"{window_prefix}-{index + 1:03d}",
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "coverage_seconds": round(window_seconds, 3),
                "reference_frame": center_item.get("file"),
                "auto_light_condition": center_item.get("auto_light_condition", "unknown"),
                "scene_conditions": [],
                "exhaustive": True,
                "is_negative": None,
                "events": [],
                "primary_review": {"reviewer": None, "status": "pending", "reviewed_at": None},
                "secondary_review": {
                    "required": None,
                    "reviewer": None,
                    "status": "pending",
                    "reviewed_at": None,
                    "agrees_with_primary": None,
                },
                "adjudication": {"required": False, "status": "not_required", "notes": ""},
            }
        )
    return windows


def build_queue(
    index_path: Path,
    inventory_path: Path,
    source: str,
    count: int = 60,
    window_seconds: float = 10.0,
    window_prefix: str = "dashcam-vn",
) -> dict:
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    with index_path.open("r", encoding="utf-8-sig", newline="") as handle:
        samples = list(csv.DictReader(handle))
    windows = choose_windows(
        samples,
        float(inventory["duration_seconds"]),
        count,
        window_seconds,
        window_prefix,
    )
    return {
        "schema_version": 1,
        "queue_type": "event_ground_truth_review",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "source_sha256": inventory["sha256"],
        "policy": {
            "target_verified_exhaustive_seconds": 600,
            "target_verified_negative_seconds": 150,
            "critical_event_types": ["fcw", "vulnerable_road_user", "cross_traffic", "lead_vehicle_braking", "fallen_rider"],
            "critical_windows_require_secondary_review": True,
            "max_pre_adjudication_disagreement_rate": 0.10,
            "allowed_event_types": EVENT_TYPES,
            "event_required_fields": [
                "event_type",
                "object_class",
                "location",
                "start_seconds",
                "hazard_onset_seconds",
                "deadline_seconds",
                "end_seconds",
            ],
            "instruction": "Review each full 10-second clip, not only the reference frame. Mark is_negative=true only when no RoadWatch event exists.",
        },
        "summary": {
            "windows": len(windows),
            "planned_coverage_seconds": round(sum(item["coverage_seconds"] for item in windows), 3),
            "verified_coverage_seconds": 0,
            "verified_negative_seconds": 0,
            "status": "pending_human_review",
        },
        "event_coverage_exceptions": {event_type: None for event_type in EVENT_TYPES},
        "windows": windows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the RW-02 event annotation queue")
    review_root = PROJECT_ROOT / "reports" / "review" / "rw01_dashcam"
    parser.add_argument("--index", type=Path, default=review_root / "selected_frames.csv")
    parser.add_argument("--inventory", type=Path, default=review_root / "inventory.json")
    parser.add_argument("--source", default="dashcam_vietnam.mp4")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.json")
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--window-seconds", type=float, default=10.0)
    parser.add_argument("--window-prefix", default="dashcam-vn")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        raise FileExistsError(f"Refusing to overwrite annotation work: {args.output}; use --force explicitly")
    queue = build_queue(
        args.index,
        args.inventory,
        args.source,
        args.count,
        args.window_seconds,
        args.window_prefix,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(queue["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
