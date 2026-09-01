"""Evaluation-only replay for an object detector candidate.

Runs a candidate and a baseline on the same sampled frames from local dashcam
videos.  This is deliberately not a training or promotion script: without
frame-level ground truth it reports coverage, class distribution, confidence
and throughput for diagnostic comparison only.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COMMON_CLASSES = (
    "person",
    "bicycle",
    "motorcycle",
    "car",
    "bus",
    "truck",
)


def model_name(names: Any, class_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(class_id, class_id))
    return str(names[class_id])


def empty_stats() -> dict[str, Any]:
    return {
        "sampled_frames": 0,
        "total_detections": 0,
        "frames_with_class": Counter(),
        "class_instances": Counter(),
        "confidence_sum": defaultdict(float),
        "confidence_count": Counter(),
        "inference_seconds": 0.0,
    }


def finalize_stats(stats: dict[str, Any]) -> dict[str, Any]:
    sampled = max(int(stats["sampled_frames"]), 1)
    classes = sorted(
        set(stats["class_instances"]) | set(stats["frames_with_class"]),
        key=str,
    )
    return {
        "sampled_frames": int(stats["sampled_frames"]),
        "total_detections": int(stats["total_detections"]),
        "frames_with_class": {
            label: int(stats["frames_with_class"][label]) for label in classes
        },
        "presence_rate": {
            label: round(stats["frames_with_class"][label] / sampled, 6)
            for label in classes
        },
        "class_instances": {
            label: int(stats["class_instances"][label]) for label in classes
        },
        "mean_confidence": {
            label: round(
                stats["confidence_sum"][label]
                / max(stats["confidence_count"][label], 1),
                6,
            )
            for label in classes
        },
        "inference_seconds": round(float(stats["inference_seconds"]), 3),
        "inference_fps": round(
            stats["sampled_frames"] / max(float(stats["inference_seconds"]), 1e-9),
            3,
        ),
    }


def update_stats(stats: dict[str, Any], result: Any) -> None:
    present: set[str] = set()
    boxes = getattr(result, "boxes", None)
    if boxes is not None:
        for box in boxes:
            class_id = int(box.cls.item())
            label = model_name(result.names, class_id)
            confidence = float(box.conf.item())
            stats["total_detections"] += 1
            stats["class_instances"][label] += 1
            stats["confidence_sum"][label] += confidence
            stats["confidence_count"][label] += 1
            present.add(label)
    for label in present:
        stats["frames_with_class"][label] += 1


def run_model(
    model: Any,
    frames: list[Any],
    stats: dict[str, Any],
    preview_indices: set[int],
    sample_start: int,
    preview_prefix: str,
    preview_dir: Path,
) -> None:
    started = time.perf_counter()
    results = model.predict(
        source=frames,
        imgsz=640,
        conf=0.25,
        iou=0.60,
        device="cpu",
        half=False,
        verbose=False,
    )
    stats["inference_seconds"] += time.perf_counter() - started
    for offset, result in enumerate(results):
        stats["sampled_frames"] += 1
        update_stats(stats, result)
        absolute_index = sample_start + offset
        if absolute_index in preview_indices:
            preview = result.plot()
            preview_dir.mkdir(parents=True, exist_ok=True)
            output = preview_dir / f"{preview_prefix}_{absolute_index:05d}.jpg"
            # OpenCV is imported lazily so the script fails clearly if it is absent.
            import cv2

            cv2.imwrite(str(output), preview)


def compare_presence(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    labels = sorted(set(COMMON_CLASSES) | {"rider"})
    return {
        label: {
            "candidate": candidate.get("presence_rate", {}).get(label, 0.0),
            "baseline": baseline.get("presence_rate", {}).get(label, 0.0),
            "delta": round(
                candidate.get("presence_rate", {}).get(label, 0.0)
                - baseline.get("presence_rate", {}).get(label, 0.0),
                6,
            ),
        }
        for label in labels
    }


def evaluate_video(
    candidate_model: Any,
    baseline_model: Any,
    video_path: Path,
    output_dir: Path,
    sample_fps: float,
    batch_size: int,
) -> dict[str, Any]:
    import cv2

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")
    source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / max(source_fps, 1e-6)
    step = max(1, round(source_fps / sample_fps))
    expected_samples = max(1, math.ceil(total_frames / step))
    preview_indices = {
        min(expected_samples - 1, round(expected_samples * fraction))
        for fraction in (0.0, 1 / 3, 2 / 3, 1.0)
    }
    preview_dir = output_dir / "previews"
    candidate_stats = empty_stats()
    baseline_stats = empty_stats()
    frames: list[Any] = []
    sample_indices: list[int] = []
    sample_ordinal = 0
    frame_index = 0

    def process_batch() -> None:
        if not frames:
            return
        run_model(
            candidate_model,
            frames,
            candidate_stats,
            preview_indices,
            sample_indices[0],
            f"{video_path.stem}_candidate",
            preview_dir,
        )
        run_model(
            baseline_model,
            frames,
            baseline_stats,
            preview_indices,
            sample_indices[0],
            f"{video_path.stem}_baseline",
            preview_dir,
        )
        frames.clear()
        sample_indices.clear()

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % step == 0:
                frames.append(frame)
                sample_indices.append(sample_ordinal)
                sample_ordinal += 1
                if len(frames) >= batch_size:
                    process_batch()
            frame_index += 1
        process_batch()
    finally:
        capture.release()

    candidate = finalize_stats(candidate_stats)
    baseline = finalize_stats(baseline_stats)
    return {
        "source": video_path.name,
        "source_bytes": video_path.stat().st_size,
        "source_fps": round(source_fps, 3),
        "duration_seconds": round(duration, 3),
        "total_source_frames": total_frames,
        "sampling": {
            "requested_fps": sample_fps,
            "frame_step": step,
            "actual_sampled_fps": round(expected_samples / max(duration, 1e-6), 3),
        },
        "candidate": candidate,
        "baseline": baseline,
        "presence_comparison": compare_presence(candidate, baseline),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay object candidate vs baseline on dashcam videos")
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, default=Path("models/yolo11n.pt"))
    parser.add_argument("--media-root", type=Path, default=Path("media"))
    parser.add_argument("--output", type=Path, default=Path("reports/object_v3_dashcam_replay_20260827.json"))
    parser.add_argument("--sample-fps", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    if args.sample_fps <= 0 or args.batch_size <= 0:
        raise ValueError("sample-fps and batch-size must be positive")
    if not args.candidate.exists():
        raise FileNotFoundError(f"Candidate model not found: {args.candidate}")
    if not args.baseline.exists():
        raise FileNotFoundError(f"Baseline model not found: {args.baseline}")

    videos = sorted(
        path
        for path in args.media_root.glob("dashcam*.mp4")
        if path.name != "dashcam_vietnam.mp4"
    )
    if not videos:
        raise FileNotFoundError("No dashcam videos found after excluding dashcam_vietnam.mp4")

    from ultralytics import YOLO

    print(f"Loading candidate: {args.candidate}", flush=True)
    candidate_model = YOLO(str(args.candidate))
    print(f"Loading baseline: {args.baseline}", flush=True)
    baseline_model = YOLO(str(args.baseline))
    output_dir = args.output.parent / f"{args.output.stem}_previews"
    results = []
    for video in videos:
        print(f"Evaluating {video.name}", flush=True)
        results.append(
            evaluate_video(
                candidate_model,
                baseline_model,
                video,
                output_dir,
                args.sample_fps,
                args.batch_size,
            )
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation_type": "same-frame-sampled-video-replay",
        "ground_truth_available": False,
        "interpretation": "Diagnostic only; not mAP/event recall and not a promotion decision.",
        "excluded_video": "dashcam_vietnam.mp4",
        "candidate": str(args.candidate),
        "baseline": str(args.baseline),
        "device": "CPU inference on local development laptop; no local training",
        "videos": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    print(f"Saved report: {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
