"""Benchmark public object detectors against the RoadWatch baseline.

This is an inference-only diagnostic benchmark. It uses identical sequential
video sampling and the same RoadWatch ONNX adapter for YOLO11n, YOLO26n and
YOLO26s. The report is not a replacement for bounding-box ground truth or the
locked event promotion gate.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.perception import OnnxYoloDetector  # noqa: E402


ROAD_CLASSES = ("person", "bicycle", "motorcycle", "car", "bus", "truck")
ROAD_CLASS_IDS = [0, 1, 2, 3, 5, 7]


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return float(ordered[index])


def new_stats() -> dict[str, Any]:
    return {
        "sampled_frames": 0,
        "total_detections": 0,
        "frames_with_class": Counter(),
        "class_instances": Counter(),
        "confidence_sum": defaultdict(float),
        "confidence_count": Counter(),
        "latencies_ms": [],
    }


def update_stats(stats: dict[str, Any], detections: list[dict[str, Any]], latency_ms: float) -> None:
    stats["sampled_frames"] += 1
    stats["latencies_ms"].append(float(latency_ms))
    present: set[str] = set()
    for detection in detections:
        label = str(detection.get("label", "unknown"))
        confidence = float(detection.get("confidence", 0.0))
        stats["total_detections"] += 1
        stats["class_instances"][label] += 1
        stats["confidence_sum"][label] += confidence
        stats["confidence_count"][label] += 1
        present.add(label)
    for label in present:
        stats["frames_with_class"][label] += 1


def finalize(stats: dict[str, Any]) -> dict[str, Any]:
    sampled = max(int(stats["sampled_frames"]), 1)
    classes = sorted(
        set(stats["class_instances"]) | set(stats["frames_with_class"]),
        key=str,
    )
    return {
        "sampled_frames": int(stats["sampled_frames"]),
        "total_detections": int(stats["total_detections"]),
        "detections_per_sampled_frame": round(
            stats["total_detections"] / sampled, 4
        ),
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
        "latency_p50_ms": round(percentile(stats["latencies_ms"], 0.50), 3),
        "latency_p95_ms": round(percentile(stats["latencies_ms"], 0.95), 3),
        "latency_mean_ms": round(
            statistics.fmean(stats["latencies_ms"]), 3
        ) if stats["latencies_ms"] else 0.0,
    }


def video_metadata(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return {"fps": 0.0, "frames": 0, "duration_seconds": 0.0}
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    capture.release()
    return {
        "fps": round(fps, 4),
        "frames": frames,
        "duration_seconds": round(frames / fps, 3) if fps > 0 else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark RoadWatch public object models")
    parser.add_argument("--video-dir", type=Path, default=PROJECT_ROOT / "media")
    parser.add_argument("--sample-fps", type=float, default=1.0)
    parser.add_argument("--runtime", choices=["cpu", "directml", "cuda"], default="directml")
    parser.add_argument("--confidence", type=float, default=0.38)
    parser.add_argument("--video", action="append", help="Specific video name; repeat for a representative subset")
    parser.add_argument("--exclude", action="append", default=["dashcam_vietnam.mp4"])
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "object_open_models_all_videos.json",
    )
    args = parser.parse_args()
    if args.sample_fps <= 0:
        raise SystemExit("--sample-fps must be positive")

    selected = set(args.video or [])
    videos = [
        path for path in sorted(args.video_dir.glob("*.mp4"))
        if path.name not in set(args.exclude) and (not selected or path.name in selected)
    ]
    if not videos:
        raise SystemExit("No benchmark videos found")

    model_paths = {
        "yolo11n_baseline": PROJECT_ROOT / "models" / "yolo11n.onnx",
        "yolo26n_public": PROJECT_ROOT / "models" / "yolo26n.onnx",
        "yolo26s_public": PROJECT_ROOT / "models" / "yolo26s.onnx",
    }
    missing = [str(path) for path in model_paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing model files: " + ", ".join(missing))

    detectors = {
        name: OnnxYoloDetector(
            path,
            confidence=args.confidence,
            image_size=640,
            runtime=args.runtime,
            allowed_classes=ROAD_CLASS_IDS,
        )
        for name, path in model_paths.items()
    }

    first_frame: Any | None = None
    for path in videos:
        capture = cv2.VideoCapture(str(path))
        ok, frame = capture.read()
        capture.release()
        if ok:
            first_frame = frame
            break
    if first_frame is None:
        raise RuntimeError("No readable video frame found")

    warmup: dict[str, float] = {}
    for name, detector in detectors.items():
        detector.load()
        started = time.perf_counter()
        detector.infer(first_frame)
        warmup[name] = round((time.perf_counter() - started) * 1000.0, 3)
        print(f"Loaded {name}: {detector.status()}", flush=True)

    model_stats: dict[str, dict[str, Any]] = {
        name: new_stats() for name in detectors
    }
    per_video: list[dict[str, Any]] = []
    total_read_failures = 0

    for path in videos:
        metadata = video_metadata(path)
        fps = max(float(metadata["fps"]), 1.0)
        step = max(1, round(fps / args.sample_fps))
        stats = {name: new_stats() for name in detectors}
        capture = cv2.VideoCapture(str(path))
        frame_index = 0
        read_failures = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % step == 0:
                for name, detector in detectors.items():
                    detections, latency = detector.infer(frame)
                    update_stats(stats[name], detections, latency)
                    update_stats(model_stats[name], detections, latency)
            frame_index += 1
        capture.release()
        total_read_failures += read_failures
        per_video.append(
            {
                "video": path.name,
                "metadata": metadata,
                "sample_step": step,
                "models": {name: finalize(stats[name]) for name in detectors},
            }
        )
        print(f"Completed {path.name}: {frame_index} source frames", flush=True)

    report = {
        "schema_version": "roadwatch-object-open-model-benchmark-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_scope": "Same sequential samples from roadwatch/media; heaviest dashcam_vietnam.mp4 excluded by default.",
        "ground_truth_available": False,
        "interpretation": "Diagnostic replay only. It cannot establish mAP or event recall without frame-level bounding-box/event ground truth.",
        "runtime_requested": args.runtime,
        "confidence_threshold": args.confidence,
        "class_taxonomy": list(ROAD_CLASSES),
        "models": {name: detector.status() for name, detector in detectors.items()},
        "warmup_ms": warmup,
        "sampling": {
            "sample_fps_requested": args.sample_fps,
            "video_count": len(videos),
            "videos": [path.name for path in videos],
            "read_failures": total_read_failures,
        },
        "aggregate": {name: finalize(model_stats[name]) for name in detectors},
        "per_video": per_video,
        "promotion_note": "Use locked event regression and human review before changing active_object_profile; baseline remains the rollback model.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["aggregate"], ensure_ascii=False, indent=2), flush=True)
    print(f"Saved report: {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
