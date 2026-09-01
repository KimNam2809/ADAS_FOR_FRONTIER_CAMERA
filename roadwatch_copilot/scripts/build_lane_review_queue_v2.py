from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/lane_candidates.json"
DEFAULT_OUTPUT = ROOT / "evaluation/rw10_lane_review_queue_v2.json"
DEFAULT_GATE = ROOT / "evaluation/rw10_lane_review_gate_v2.json"
SOURCE_HASHES = {
    item["source"]: item.get("source_sha256")
    for item in json.loads((ROOT / "evaluation/rw10_lane_annotation_queue.json").read_text(encoding="utf-8")).get("records", [])
    if item.get("source_sha256")
}
PRIORITY = {"rain_night": 0, "night": 1, "dense_traffic": 2, "day": 3}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_queue(payload: dict, artifact_root: str) -> dict:
    records = []
    for index, item in enumerate(payload.get("records", [])):
        condition = str(item.get("condition", "unknown"))
        source = str(item["source"])
        review_image = f"{artifact_root}/review_frames/{item['review_image']}"
        records.append(
            {
                "id": item["id"],
                "source": source,
                "source_sha256": SOURCE_HASHES.get(source),
                "split": item.get("split"),
                "timestamp_s": item.get("timestamp_s"),
                "frame_index": item.get("frame_index"),
                "conditions": [condition],
                "image": review_image,
                "review_priority": PRIORITY.get(condition, 9),
                "priority_reason": "hard_condition_first",
                "model_proposal": {
                    "label_status": item.get("label_status"),
                    "accepted": bool(item.get("accepted", False)),
                    "rejection_reasons": item.get("rejection_reasons", []),
                    "lane_instances": item.get("lane_instances", []),
                    "geometry": item.get("geometry", {}),
                },
                "review_status": "pending",
                "ground_truth_lane_count": None,
                "ego_left_boundary": [],
                "ego_right_boundary": [],
                "marking_type": [],
                "visibility": None,
                "road_direction": None,
                "uncertain": None,
                "predicted_lane_count": None,
                "ego_boundary_f1": None,
                "ldw_false_alerts": 0,
                "measured_seconds": 0,
                "reviewer": None,
                "review_notes": "",
                "_source_order": index,
            }
        )
    records.sort(key=lambda item: (item["review_priority"], item["source"], item["timestamp_s"], item["_source_order"]))
    for item in records:
        item.pop("_source_order", None)
    return {
        "schema_version": 2,
        "task_id": "RW-10",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_artifact": "Lane V2 Version 3 candidate_unverified output",
        "annotation_policy": "Human must confirm ordered lane polylines; model proposals are not ground truth.",
        "review_status_policy": ["pending", "verified", "rejected"],
        "annotation_instruction": {
            "lane_count": "Count visible same-direction lane instances, not opposing lanes or turn-only fragments.",
            "ego_boundaries": "Annotate left/right ego lane polylines only when defensible; otherwise set uncertain=true and explain.",
            "visibility": ["clear", "partial", "occluded", "not_visible"],
            "marking_type": ["solid", "dashed", "double", "curb", "unknown"],
            "road_direction": ["same_direction", "opposing", "unknown"],
            "double_review": "At least 300 frames must receive independent second review; disagreement <= 0.05.",
        },
        "split_policy": "Video-grouped; source video must remain in one split.",
        "records": records,
    }


def validate_queue(queue: dict) -> dict:
    records = queue.get("records", [])
    ids = [item.get("id") for item in records]
    sources_by_split: dict[str, set[str]] = {}
    invalid = []
    for item in records:
        split = str(item.get("split"))
        sources_by_split.setdefault(split, set()).add(str(item.get("source")))
        if item.get("review_status") != "pending":
            invalid.append(f"{item.get('id')}:review_status")
        if item.get("ground_truth_lane_count") is not None or item.get("predicted_lane_count") is not None:
            invalid.append(f"{item.get('id')}:ground_truth_prefilled")
        if item.get("ego_left_boundary") or item.get("ego_right_boundary"):
            invalid.append(f"{item.get('id')}:polyline_prefilled")
    split_values = list(sources_by_split.values())
    overlaps = any(split_values[i] & split_values[j] for i in range(len(split_values)) for j in range(i + 1, len(split_values)))
    return {
        "status": "pass" if len(ids) == len(set(ids)) and not invalid and not overlaps else "fail",
        "records": len(records),
        "unique_ids": len(set(ids)),
        "sources_by_split": {key: sorted(value) for key, value in sources_by_split.items()},
        "split_source_overlap": overlaps,
        "invalid_fields": invalid,
        "pending_records": sum(item.get("review_status") == "pending" for item in records),
        "candidate_records": sum(item.get("model_proposal", {}).get("accepted") is True for item in records),
        "rejected_by_model_records": sum(item.get("model_proposal", {}).get("accepted") is False for item in records),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a human-reviewable RW-10 lane queue")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--gate-output", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--artifact-root", default="artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    queue = build_queue(payload, args.artifact_root)
    validation = validate_queue(queue)
    queue["validation"] = validation
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    gate = {
        "schema_version": 2,
        "task_id": "RW-10",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_human_review",
        "training_blocked": True,
        "queue_validation": validation,
        "required_before_finetune": {
            "verified_frames_min": 3000,
            "double_review_frames_min": 300,
            "night_verified_min": 500,
            "rain_night_verified_min": 400,
            "multi_lane_verified_min": 1000,
            "faded_or_missing_marking_verified_min": 400,
            "review_disagreement_max": 0.05,
        },
        "human_action": "Fill ground_truth fields and review_status per record; do not copy model_proposal blindly.",
    }
    args.gate_output.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"queue": str(args.output), "gate": str(args.gate_output), **validation}, ensure_ascii=False, indent=2))
    return 0 if validation["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
