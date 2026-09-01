from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Visual review of 20-frame/10-second storyboards. Offsets are relative to the
# beginning of each queue window so regeneration remains deterministic.
CANDIDATES: dict[int, list[dict]] = {
    1: [{"event_type": "cross_traffic", "object_class": "motorcycle", "location": "left_to_right", "offsets": [0.4, 1.0, 3.0, 6.0], "confidence": 0.55}],
    4: [{"event_type": "cross_traffic", "object_class": "car", "location": "left_to_right", "offsets": [2.0, 3.0, 5.0, 7.0], "confidence": 0.45}],
    7: [{"event_type": "cross_traffic", "object_class": "motorcycle", "location": "right_to_left", "offsets": [1.5, 2.5, 4.5, 7.0], "confidence": 0.50}],
    14: [{"event_type": "cut_in", "object_class": "car", "location": "left", "offsets": [2.5, 3.5, 5.5, 7.5], "confidence": 0.55}],
    17: [{"event_type": "cut_in", "object_class": "car", "location": "left", "offsets": [2.0, 3.0, 5.0, 7.5], "confidence": 0.45}],
    18: [{"event_type": "cut_in", "object_class": "car", "location": "left", "offsets": [1.0, 2.0, 4.5, 7.5], "confidence": 0.50}],
    21: [{"event_type": "cross_traffic", "object_class": "bus", "location": "left_to_right", "offsets": [0.0, 0.8, 2.2, 4.0], "confidence": 0.65}],
    26: [{"event_type": "cut_in", "object_class": "car", "location": "left", "offsets": [0.0, 0.8, 2.5, 4.5], "confidence": 0.60}],
    27: [{"event_type": "cut_in", "object_class": "car", "location": "left", "offsets": [0.0, 1.0, 3.0, 5.5], "confidence": 0.55}],
    29: [{"event_type": "cross_traffic", "object_class": "motorcycle", "location": "right_to_left", "offsets": [0.5, 1.5, 3.5, 6.0], "confidence": 0.45}],
    30: [{"event_type": "cross_traffic", "object_class": "motorcycle", "location": "right_to_left", "offsets": [0.5, 1.5, 3.5, 6.0], "confidence": 0.45}],
    37: [{"event_type": "speed_sign", "object_class": "traffic_sign", "location": "right", "offsets": [4.5, 5.0, 7.0, 8.5], "confidence": 0.80, "speed_value": 50}],
    39: [{"event_type": "cut_in", "object_class": "car", "location": "left", "offsets": [0.0, 1.0, 3.0, 5.5], "confidence": 0.45}],
    48: [{"event_type": "cut_in", "object_class": "car", "location": "right", "offsets": [0.0, 1.0, 3.5, 6.0], "confidence": 0.55}],
    50: [{"event_type": "cut_in", "object_class": "car", "location": "right", "offsets": [2.0, 3.0, 5.0, 7.0], "confidence": 0.50}],
    51: [{"event_type": "cross_traffic", "object_class": "motorcycle", "location": "left_to_right", "offsets": [0.0, 1.0, 3.0, 5.5], "confidence": 0.50}],
}

INTERSECTIONS = {1, 3, 4, 7, 8, 9, 10, 12, 13, 14, 17, 20, 21, 24, 25, 27, 28, 29, 30, 34, 35, 39, 40, 43, 45, 49, 50, 51, 53, 54}
DENSE_TRAFFIC = set(range(1, 19)) | set(range(20, 32)) | {34, 35, 39, 40, 41, 43, 45, 49, 50, 51}
INTERNAL_ROAD = {52, 53, 54, 55, 56, 57, 58, 59, 60}
CRITICAL = {"fcw", "vulnerable_road_user", "cross_traffic", "lead_vehicle_braking", "fallen_rider"}


def bootstrap(payload: dict) -> dict:
    result = copy.deepcopy(payload)
    generated_at = datetime.now(timezone.utc).isoformat()
    for index, window in enumerate(result["windows"], start=1):
        scene_conditions = ["day"]
        if index in INTERSECTIONS:
            scene_conditions.append("intersection")
        if index in DENSE_TRAFFIC:
            scene_conditions.append("dense_traffic")
        if index in INTERNAL_ROAD:
            scene_conditions.append("internal_road")
        window["scene_conditions"] = scene_conditions
        window["storyboard"] = f"reports/review/rw02_storyboards/dashcam-vn-{index:03d}.jpg"
        events = []
        for event_number, candidate in enumerate(CANDIDATES.get(index, []), start=1):
            start = float(window["start_seconds"])
            offsets = candidate["offsets"]
            event = {
                "id": f"ai-{window['window_id']}-{event_number}",
                "event_type": candidate["event_type"],
                "object_class": candidate["object_class"],
                "location": candidate["location"],
                "start_seconds": round(start + offsets[0], 3),
                "hazard_onset_seconds": round(start + offsets[1], 3),
                "deadline_seconds": round(start + offsets[2], 3),
                "end_seconds": round(start + offsets[3], 3),
                "review_status": "ai_provisional",
                "confidence": candidate["confidence"],
                "notes": "Storyboard visual candidate; requires full-motion Human audit.",
            }
            if "speed_value" in candidate:
                event["speed_value"] = candidate["speed_value"]
            events.append(event)
        window["events"] = events
        window["is_negative"] = not bool(events)
        window["primary_review"] = {
            "reviewer": "codex_visual_bootstrap",
            "status": "ai_provisional",
            "reviewed_at": generated_at,
        }
        window["secondary_review"]["required"] = any(
            event["event_type"] in CRITICAL for event in events
        )
        window["review_priority"] = "high" if events else "medium" if index in DENSE_TRAFFIC else "low"
        window["provisional_confidence"] = (
            max((float(event["confidence"]) for event in events), default=0.82)
            if events
            else (0.70 if index in DENSE_TRAFFIC else 0.86)
        )
        window["provisional_notes"] = (
            "Potential event candidate; inspect full 10-second clip."
            if events
            else "No alert-worthy event visible in 2 FPS storyboard; temporal hazards may still be missed."
        )

    candidate_windows = sum(bool(window["events"]) for window in result["windows"])
    provisional_negative_seconds = sum(
        float(window["coverage_seconds"])
        for window in result["windows"]
        if window["is_negative"]
    )
    result["ai_bootstrap"] = {
        "status": "complete_provisional_not_ground_truth",
        "generated_at": generated_at,
        "method": "20-frame storyboard visual review at approximately 2 FPS",
        "reviewed_windows": len(result["windows"]),
        "candidate_windows": candidate_windows,
        "provisional_negative_windows": len(result["windows"]) - candidate_windows,
        "provisional_negative_seconds": provisional_negative_seconds,
        "limitations": [
            "Not independent Human ground truth and cannot pass promotion gate.",
            "2 FPS storyboards can miss short braking, cut-in and lane-departure dynamics.",
            "No ego speed, CAN, depth or calibrated TTC was available.",
            "Full-motion audit is mandatory for all high-priority windows and a sample of negatives.",
        ],
    }
    result["summary"].update(
        {
            "status": "ai_provisional_complete_human_audit_pending",
            "ai_provisional_windows": len(result["windows"]),
            "ai_candidate_windows": candidate_windows,
            "ai_provisional_negative_seconds": provisional_negative_seconds,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap RW-02 AI-provisional annotations")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.ai_provisional.json",
    )
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = bootstrap(payload)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["ai_bootstrap"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
