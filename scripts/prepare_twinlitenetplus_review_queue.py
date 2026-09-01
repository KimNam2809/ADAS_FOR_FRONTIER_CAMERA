from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "evaluation" / "rw10_lane_ai_provisional_queue_20260827.json"
DEFAULT_OUTPUT = ROOT / "evaluation" / "twinlitenetplus_ground_truth_review_queue_v1.json"
DEFAULT_FRAMES_DIR = (
    ROOT
    / "artifacts"
    / "kaggle"
    / "lane_v2_v3_output"
    / "lane_v2_quality_gate"
    / "review_frames"
)

CONDITION_PRIORITY = {
    "rain_night": 0,
    "night": 1,
    "dense_traffic": 2,
    "day": 3,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def priority_for(record: dict[str, Any]) -> tuple[int, str]:
    conditions = [str(item) for item in record.get("conditions") or []]
    if not conditions:
        return 99, "condition_not_declared"
    priority = min(CONDITION_PRIORITY.get(condition, 98) for condition in conditions)
    return priority, "hard_condition_first" if priority <= 1 else "coverage_order"


def relative_to_root(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    priority, reason = priority_for(record)
    return {
        "id": str(record.get("id")),
        "source": str(record.get("source")),
        "source_sha256": record.get("source_sha256"),
        "split": "test",
        "timestamp_s": float(record.get("timestamp_s") or 0.0),
        "frame_index": record.get("frame_index"),
        "conditions": [str(item) for item in record.get("conditions") or []],
        "image": str(record.get("image")),
        "review_priority": priority,
        "priority_reason": reason,
        # Deliberately blank: these values must be entered after human inspection.
        "ground_truth_lane_count": None,
        "ego_left_boundary": [],
        "ego_right_boundary": [],
        "marking_type": ["unknown"],
        "visibility": "not_visible",
        "road_direction": "unknown",
        "uncertain": None,
        "review_status": "pending",
        "reviewer": "",
        "review_notes": "",
    }


def build(input_path: Path, output_path: Path, frames_dir: Path, min_records: int) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise ValueError("Input queue does not contain a records list")

    test_records = [
        item
        for item in records
        if isinstance(item, dict) and str(item.get("split") or "") == "test"
    ]
    test_records.sort(
        key=lambda item: (
            priority_for(item)[0],
            float(item.get("timestamp_s") or 0.0),
            str(item.get("id")),
        )
    )
    if len(test_records) < min_records:
        raise ValueError(f"Only {len(test_records)} test records found; need at least {min_records}")

    cleaned = [clean_record(item) for item in test_records]
    ids = [item["id"] for item in cleaned]
    duplicate_ids = sorted({item for item, count in Counter(ids).items() if count > 1})
    if duplicate_ids:
        raise ValueError(f"Duplicate record IDs: {duplicate_ids[:5]}")

    missing_images = []
    for item in cleaned:
        image_path = ROOT / item["image"]
        if not image_path.exists():
            # The review app resolves images by basename under --frames-dir.
            image_path = frames_dir / Path(item["image"]).name
        if not image_path.exists():
            missing_images.append(item["image"])
    if missing_images:
        raise FileNotFoundError(
            f"Missing {len(missing_images)} review frames; first: {missing_images[:3]}"
        )

    conditions = Counter(
        condition
        for item in cleaned
        for condition in item.get("conditions", [])
    )
    source_counts = Counter(item["source"] for item in cleaned)
    output = {
        "schema_version": "roadwatch-lane-review-queue-v1",
        "task_id": "RW-10.3-TwinLiteNetPlus-ground-truth-prep",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_queue": relative_to_root(input_path),
        "source_queue_sha256": sha256(input_path),
        "purpose": "Independent human review before TwinLiteNet+ versus YOLOP evaluation",
        "ground_truth_status": "not_ready_pending_human_review",
        "ground_truth_independent_of_models": True,
        "selection": {
            "requested_split": "test",
            "selected_records": len(cleaned),
            "minimum_records_for_pilot": min_records,
            "ordering": ["rain_night", "night", "dense_traffic", "day", "other"],
            "source_grouped_split": True,
        },
        "annotation_contract": {
            "never_copy_model_proposal": True,
            "eligible_for_builder_only_when": [
                "review_status == verified",
                "reviewer is a human reviewer",
                "uncertain == false",
                "lane count and boundaries are visually defensible",
            ],
            "hard_cases": "Use uncertain=true when markings are not defensible; do not guess.",
            "boundary_semantics": "Mark left and right ego-lane boundaries only; use ordered [x,y] points.",
            "drivable_area": "Not annotated by this queue; no drivable-area metric may be claimed.",
            "double_review": "A second human must independently review the pilot subset before promotion.",
        },
        "summary": {
            "records": len(cleaned),
            "conditions": dict(conditions),
            "sources": dict(source_counts),
            "review_status": {"pending": len(cleaned)},
            "verified": 0,
            "missing_images": 0,
        },
        "records": cleaned,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a clean, model-independent held-out lane review queue."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--frames-dir", type=Path, default=DEFAULT_FRAMES_DIR)
    parser.add_argument("--min-records", type=int, default=300)
    args = parser.parse_args()

    result = build(args.input, args.output, args.frames_dir, args.min_records)
    print(
        json.dumps(
            {
                "status": result["ground_truth_status"],
                "output": str(args.output),
                "summary": result["summary"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
