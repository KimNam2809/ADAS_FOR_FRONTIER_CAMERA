from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "evaluation" / "rw10_lane_review_queue_v2.json"
DEFAULT_OUTPUT = ROOT / "evaluation" / "twinlitenetplus_ground_truth_v1"
AI_REVIEWERS = {
    "Gemini_2.5_Flash",
    "gemini_api_mixed",
    "Codex_AI_Assisted_Reviewer",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_source(source: str) -> Path:
    candidates = [ROOT / "media" / source]
    if source == "dashcam_vietnam_rainnight.mp4":
        candidates.append(ROOT / "media" / "dashcam_vietnam_rain+night.mp4")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Source video not found for {source}: {candidates}")


def point_list(value: Any) -> list[list[float]]:
    if not isinstance(value, list):
        return []
    result: list[list[float]] = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return []
        try:
            x, y = float(point[0]), float(point[1])
        except (TypeError, ValueError):
            return []
        if not math.isfinite(x) or not math.isfinite(y):
            return []
        result.append([x, y])
    return result


def validate_polyline(points: list[list[float]], width: int, height: int) -> str | None:
    if len(points) < 2:
        return "boundary_requires_at_least_two_points"
    for x, y in points:
        if x < 0 or x >= width or y < 0 or y >= height:
            return "boundary_point_out_of_frame"
    return None


def human_verified(record: dict[str, Any]) -> tuple[bool, str]:
    if record.get("review_status") != "verified":
        return False, "review_status_not_verified"
    reviewer = str(record.get("reviewer") or "").strip()
    if not reviewer:
        return False, "missing_reviewer"
    if reviewer in AI_REVIEWERS or "gemini" in reviewer.lower() or "codex" in reviewer.lower():
        return False, "ai_reviewer_not_ground_truth"
    if record.get("uncertain") is not False:
        return False, "uncertain_record"
    return True, "eligible"


def validate_record(record: dict[str, Any], width: int, height: int) -> tuple[bool, str, dict[str, Any]]:
    eligible, reason = human_verified(record)
    left = point_list(record.get("ego_left_boundary"))
    right = point_list(record.get("ego_right_boundary"))
    try:
        lane_count = int(record.get("ground_truth_lane_count"))
    except (TypeError, ValueError):
        lane_count = -1
    if eligible and lane_count < 0:
        eligible, reason = False, "invalid_lane_count"
    if eligible and lane_count == 0 and (left or right):
        eligible, reason = False, "zero_lane_count_with_boundary"
    if eligible and lane_count > 0:
        left_error = validate_polyline(left, width, height)
        right_error = validate_polyline(right, width, height)
        if left_error or right_error:
            eligible, reason = False, left_error or right_error or "invalid_boundary"
    cleaned = {
        "id": str(record.get("id")),
        "source": str(record.get("source")),
        "source_sha256": record.get("source_sha256"),
        "split": str(record.get("split") or "test"),
        "timestamp_s": float(record.get("timestamp_s") or 0.0),
        "frame_index": record.get("frame_index"),
        "conditions": record.get("conditions") or [],
        "ground_truth_lane_count": lane_count,
        "ego_left_boundary": left,
        "ego_right_boundary": right,
        "marking_type": record.get("marking_type") or ["unknown"],
        "visibility": record.get("visibility"),
        "road_direction": record.get("road_direction"),
        "uncertain": record.get("uncertain"),
        "review_status": record.get("review_status"),
        "reviewer": record.get("reviewer"),
        "review_notes": record.get("review_notes", ""),
    }
    return eligible, reason, cleaned


def extract_frame(source_path: Path, timestamp_s: float) -> np.ndarray:
    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open source video: {source_path}")
    capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp_s) * 1000.0)
    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        raise RuntimeError(f"Cannot read frame at {timestamp_s}s from {source_path}")
    return frame


def write_boundary_mask(frame: np.ndarray, record: dict[str, Any], path: Path) -> None:
    height, width = frame.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    for points in (record["ego_left_boundary"], record["ego_right_boundary"]):
        if len(points) >= 2:
            cv2.polylines(
                mask,
                [np.asarray(points, dtype=np.int32)],
                False,
                255,
                thickness=5,
                lineType=cv2.LINE_AA,
            )
    cv2.imwrite(str(path), mask)


def build(
    queue: dict[str, Any],
    output_dir: Path,
    min_records: int,
    evaluation_splits: set[str],
    queue_path: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / "frames"
    masks_dir = output_dir / "lane_boundary_masks"
    frames_dir.mkdir(exist_ok=True)
    masks_dir.mkdir(exist_ok=True)
    records = queue.get("records", [])
    manifest_records: list[dict[str, Any]] = []
    rejection_reasons: Counter[str] = Counter()
    source_dimensions: dict[str, list[int]] = {}
    for source in sorted({str(item.get("source")) for item in records}):
        try:
            capture = cv2.VideoCapture(str(resolve_source(source)))
            source_dimensions[source] = [
                int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            ]
            capture.release()
        except (FileNotFoundError, RuntimeError):
            source_dimensions[source] = [0, 0]

    considered_records = [
        item for item in records if str(item.get("split") or "") in evaluation_splits
    ]
    for item in considered_records:
        source = str(item.get("source"))
        width, height = source_dimensions.get(source, [0, 0])
        eligible, reason, cleaned = validate_record(item, width, height)
        if not eligible:
            rejection_reasons[reason] += 1
            continue
        try:
            frame = extract_frame(resolve_source(source), cleaned["timestamp_s"])
        except (FileNotFoundError, RuntimeError) as exc:
            rejection_reasons[f"frame_extraction_failed:{type(exc).__name__}"] += 1
            continue
        safe_id = cleaned["id"].replace("/", "_").replace("\\", "_")
        frame_path = frames_dir / f"{safe_id}.jpg"
        mask_path = masks_dir / f"{safe_id}.png"
        cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        write_boundary_mask(frame, cleaned, mask_path)
        cleaned["frame_path"] = str(frame_path.relative_to(ROOT)).replace("\\", "/")
        cleaned["lane_boundary_mask_path"] = str(mask_path.relative_to(ROOT)).replace("\\", "/")
        cleaned["drivable_mask_available"] = False
        manifest_records.append(cleaned)

    by_condition = Counter(
        condition
        for item in manifest_records
        for condition in item.get("conditions", [])
    )
    human_verified_count = len(manifest_records)
    status = "ready_for_model_comparison" if human_verified_count >= min_records else "blocked_insufficient_human_ground_truth"
    manifest = {
        "schema_version": "roadwatch-lane-ground-truth-v1",
        "task_id": "TwinLiteNetPlus-vs-YOLOP",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "ground_truth_independent_of_models": True,
        "source_queue": str(queue_path.resolve().relative_to(ROOT)).replace("\\", "/"),
        "source_queue_sha256": sha256(queue_path.resolve()),
        "evaluation_splits": sorted(evaluation_splits),
        "policy": {
            "accepted_only_when": [
                "review_status == verified",
                "reviewer is human and not AI-assisted",
                "uncertain == false",
                "valid lane count and ego boundaries",
            ],
            "model_proposals_are_never_ground_truth": True,
            "drivable_area": "not available from the current lane polyline queue",
            "lane_mask": "rasterized ego-boundary polylines, thickness 5 pixels, for boundary evaluation only",
        },
        "source_dimensions": source_dimensions,
        "summary": {
            "queue_records": len(records),
            "records_in_evaluation_splits": len(considered_records),
            "human_verified_records": human_verified_count,
            "minimum_records_for_comparison": min_records,
            "conditions": dict(by_condition),
            "rejection_reasons": dict(rejection_reasons),
        },
        "records": manifest_records,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "records.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in manifest_records),
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "summary": manifest["summary"], "manifest": str(manifest_path)}, ensure_ascii=False, indent=2))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build independent lane ground truth for model evaluation.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--min-records", type=int, default=300)
    parser.add_argument(
        "--splits",
        default="test",
        help="Comma-separated evaluation splits. Default test; never include train for final comparison.",
    )
    args = parser.parse_args()
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    evaluation_splits = {item.strip() for item in args.splits.split(",") if item.strip()}
    if not evaluation_splits:
        raise SystemExit("--splits must contain at least one split")
    manifest = build(queue, args.output_dir, args.min_records, evaluation_splits, args.queue)
    return 0 if manifest["status"] == "ready_for_model_comparison" else 2


if __name__ == "__main__":
    raise SystemExit(main())
