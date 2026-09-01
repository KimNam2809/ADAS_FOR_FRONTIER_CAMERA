"""Offline UFLDv2 auto-pass for records the Gemini quota could not cover.

This is explicitly an AI provisional inference, not Human review.  It fills
only the isolated sidecar and records the local model source on each item.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.perception import UFLDv2LaneDetector  # noqa: E402


MODEL_SOURCE = "ufldv2_culane_res18_320x1600.onnx"
AI_REVIEWER = "Codex_AI_Assisted_Reviewer"


def image_path(record: dict[str, Any]) -> Path:
    candidate = ROOT / str(record.get("image", ""))
    if candidate.exists():
        return candidate
    return ROOT / "artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/review_frames" / f"{record['id']}.jpg"


def provisional_from_output(output: dict[str, Any], conditions: list[str]) -> dict[str, Any]:
    lanes = output.get("lane_instances") or []
    ego = [lane for lane in lanes if lane.get("role") == "ego_boundary"]
    left = next((lane.get("points", []) for lane in ego if lane.get("lane_id") == 1), [])
    right = next((lane.get("points", []) for lane in ego if lane.get("lane_id") == 2), [])
    quality = float(output.get("quality", 0.0))
    has_boundary = bool(left or right)
    if not has_boundary:
        lane_count = 0
        left = []
        right = []
        visibility = "not_visible"
        marking = ["unknown"]
    else:
        lane_count = 1
        visibility = "clear" if quality >= 0.75 and len(left) >= 20 and len(right) >= 20 else "partial"
        marking = ["unknown", "unknown"]
    return {
        "ground_truth_lane_count": lane_count,
        "ego_left_boundary": left,
        "ego_right_boundary": right,
        "marking_type": marking,
        "visibility": visibility,
        "road_direction": "same_direction",
        "uncertain": True if visibility != "clear" or any(c in {"night", "rain_night"} for c in conditions) else False,
        "review_notes": f"AI provisional local inference from {MODEL_SOURCE}; quality={quality:.3f}; requires Human adjudication.",
        "review_status": "ai_provisional",
        "reviewer": AI_REVIEWER,
        "ai_review_model": MODEL_SOURCE,
        "ai_review_eligible_as_human": False,
        "ai_review_eligible_as_double_review": False,
    }


def run(queue_path: Path, max_frames: int | None = None, checkpoint: int = 25) -> dict[str, Any]:
    data = json.loads(queue_path.read_text(encoding="utf-8"))
    records = data.get("records", [])
    detector = UFLDv2LaneDetector(ConfigManager.model_path(MODEL_SOURCE), runtime="cpu")
    todo = [r for r in records if r.get("review_status") != "ai_provisional"]
    if max_frames is not None:
        todo = todo[:max_frames]
    errors: dict[str, str] = {}
    processed = 0
    for record in todo:
        path = image_path(record)
        frame = cv2.imread(str(path)) if path.exists() else None
        if frame is None:
            record["review_status"] = "ai_error"
            record["reviewer"] = AI_REVIEWER
            errors[record["id"]] = "missing_image"
            continue
        output, latency_ms = detector.infer(frame)
        if detector.error:
            record["review_status"] = "ai_error"
            record["reviewer"] = AI_REVIEWER
            record["ai_error"] = detector.error
            errors[record["id"]] = detector.error
            continue
        record.update(provisional_from_output(output, record.get("conditions", [])))
        record["ai_review_latency_ms"] = round(float(latency_ms), 3)
        processed += 1
        if processed % max(1, checkpoint) == 0:
            queue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"checkpoint processed={processed} errors={len(errors)}", flush=True)
    data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    data["provenance"] = {
        "review_status": "ai_provisional",
        "reviewer": AI_REVIEWER,
        "eligible_as_human_review": False,
        "eligible_as_double_review": False,
        "local_model": MODEL_SOURCE,
    }
    queue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"total_records": len(records), "processed_local": processed, "ai_provisional": sum(1 for r in records if r.get("review_status") == "ai_provisional"), "ai_errors": sum(1 for r in records if r.get("review_status") == "ai_error"), "errors": errors}
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=ROOT / "evaluation/rw10_lane_ai_provisional_queue_20260827.json")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--checkpoint", type=int, default=25)
    args = parser.parse_args()
    run(args.queue, args.max_frames, args.checkpoint)


if __name__ == "__main__":
    main()
