"""Benchmark the new layer1_test artifacts against RoadWatch production heads.

This is an inference-only diagnostic benchmark. It deliberately keeps the
production configuration untouched and reports task-specific proxy metrics
when local ground truth is unavailable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.perception import YOLOPSegmenter  # noqa: E402


VIDEO_CANDIDATES = (
    "dashcam_vietnam_night.mp4",
    "dashcam_vietnam_rain+night.mp4",
    "dashcam_vietnam_traffic_multi.mp4",
)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def video_metadata(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return {"fps": 0.0, "frames": 0, "duration_s": 0.0, "width": 0, "height": 0}
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    result = {
        "fps": round(fps, 4),
        "frames": frames,
        "duration_s": round(frames / fps, 3) if fps > 0 else 0.0,
        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
    }
    capture.release()
    return result


def load_frame(path: Path, timestamp_s: float) -> np.ndarray | None:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return None
    capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp_s) * 1000.0)
    ok, frame = capture.read()
    capture.release()
    return frame if ok else None


def sample_timestamps(metadata: dict[str, Any], count: int) -> list[float]:
    duration = float(metadata.get("duration_s") or 0.0)
    if duration <= 0.0:
        return []
    # Use identical, deterministic timestamps for all six compared runtimes.
    fractions = np.linspace(0.05, 0.95, max(1, count))
    return [round(float(duration * fraction), 3) for fraction in fractions]


def model_label(names: Any, class_id: int) -> str:
    if isinstance(names, dict):
        return str(names.get(class_id, class_id))
    return str(names[class_id])


def new_detection_stats() -> dict[str, Any]:
    return {
        "sampled_frames": 0,
        "frames_with_detection": 0,
        "total_detections": 0,
        "class_instances": Counter(),
        "frames_with_class": Counter(),
        "confidence_sum": defaultdict(float),
        "confidence_count": Counter(),
        "latencies_ms": [],
        "errors": [],
    }


def update_detection_stats(stats: dict[str, Any], result: Any) -> None:
    boxes = getattr(result, "boxes", None)
    frame_has_detection = False
    present: set[str] = set()
    if boxes is not None:
        for box in boxes:
            class_id = int(box.cls.item())
            label = model_label(result.names, class_id)
            confidence = float(box.conf.item())
            frame_has_detection = True
            stats["total_detections"] += 1
            stats["class_instances"][label] += 1
            stats["frames_with_class"][label] += 0
            stats["confidence_sum"][label] += confidence
            stats["confidence_count"][label] += 1
            present.add(label)
    if frame_has_detection:
        stats["frames_with_detection"] += 1
    for label in present:
        stats["frames_with_class"][label] += 1


def finalize_detection_stats(stats: dict[str, Any]) -> dict[str, Any]:
    sampled = max(int(stats["sampled_frames"]), 1)
    labels = sorted(
        set(stats["class_instances"]) | set(stats["frames_with_class"]), key=str
    )
    latencies = [float(value) for value in stats["latencies_ms"]]
    return {
        "sampled_frames": int(stats["sampled_frames"]),
        "frames_with_detection": int(stats["frames_with_detection"]),
        "frame_detection_rate": round(stats["frames_with_detection"] / sampled, 4),
        "total_detections": int(stats["total_detections"]),
        "detections_per_frame": round(stats["total_detections"] / sampled, 4),
        "frames_with_class": {
            label: int(stats["frames_with_class"][label]) for label in labels
        },
        "class_presence_rate": {
            label: round(stats["frames_with_class"][label] / sampled, 4)
            for label in labels
        },
        "class_instances": {
            label: int(stats["class_instances"][label]) for label in labels
        },
        "mean_confidence": {
            label: round(
                stats["confidence_sum"][label]
                / max(stats["confidence_count"][label], 1),
                4,
            )
            for label in labels
        },
        "latency_ms": {
            "p50": round(percentile(latencies, 0.50), 3),
            "p95": round(percentile(latencies, 0.95), 3),
            "mean": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        },
        "errors": stats["errors"],
    }


def run_ultralytics_frame(model: Any, frame: np.ndarray, imgsz: int) -> tuple[Any, float]:
    started = time.perf_counter()
    result = model.predict(
        source=frame,
        imgsz=imgsz,
        conf=0.25,
        iou=0.60,
        device="cpu",
        half=False,
        verbose=False,
    )[0]
    return result, (time.perf_counter() - started) * 1000.0


def detection_status(model: Any, path: Path, imgsz: int) -> dict[str, Any]:
    return {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "sha256": sha256(path),
        "task": str(model.task),
        "imgsz_used": imgsz,
        "names": {str(key): str(value) for key, value in model.names.items()},
        "overrides": {
            key: str(value)
            for key, value in getattr(model, "overrides", {}).items()
            if key in {"task", "data", "imgsz", "model"}
        },
    }


class YoloPv2Lane:
    """CPU adapter for the TorchScript YOLOPv2 artifact in layer1_test."""

    def __init__(self, model_path: Path, vendor_dir: Path) -> None:
        import torch

        if not vendor_dir.exists():
            raise FileNotFoundError(f"YOLOPv2 vendor utils not found: {vendor_dir}")
        sys.path.insert(0, str(vendor_dir))
        from utils.utils import driving_area_mask, lane_line_mask, letterbox

        self.torch = torch
        self.driving_area_mask = driving_area_mask
        self.lane_line_mask = lane_line_mask
        self.letterbox = letterbox
        self.model_path = model_path
        self.model = torch.jit.load(str(model_path), map_location="cpu").eval()
        self.provider = "TorchScript/CPU"
        self.error: str | None = None

    def infer(self, frame: np.ndarray) -> tuple[dict[str, Any], float]:
        started = time.perf_counter()
        height, width = frame.shape[:2]
        try:
            image, _, _ = self.letterbox(frame, new_shape=640, auto=True)
            rgb = image[:, :, ::-1].transpose(2, 0, 1)
            rgb = np.ascontiguousarray(rgb)
            tensor = self.torch.from_numpy(rgb).float().unsqueeze(0) / 255.0
            with self.torch.no_grad():
                _, seg, ll = self.model(tensor)
                drive = self.driving_area_mask(seg)
                lane = self.lane_line_mask(ll)
            if hasattr(drive, "cpu"):
                drive = drive.cpu().numpy()
            if hasattr(lane, "cpu"):
                lane = lane.cpu().numpy()
            drive = np.asarray(drive).squeeze().astype(np.uint8)
            lane = np.asarray(lane).squeeze().astype(np.uint8)
            drive = cv2.resize(drive, (width, height), interpolation=cv2.INTER_NEAREST)
            lane = cv2.resize(lane, (width, height), interpolation=cv2.INTER_NEAREST)
            return {
                "lane_mask": lane,
                "drivable_mask": drive,
                "lane_pixels": int(np.count_nonzero(lane)),
                "drivable_pixels": int(np.count_nonzero(drive)),
                "quality": round(lane_quality(lane), 4),
                "provider": self.provider,
            }, (time.perf_counter() - started) * 1000.0
        except Exception as exc:
            self.error = str(exc)
            return {
                "lane_mask": np.zeros((height, width), dtype=np.uint8),
                "drivable_mask": np.zeros((height, width), dtype=np.uint8),
                "lane_pixels": 0,
                "drivable_pixels": 0,
                "quality": 0.0,
                "provider": self.provider,
            }, (time.perf_counter() - started) * 1000.0

    def status(self) -> dict[str, Any]:
        return {
            "file": str(self.model_path.relative_to(PROJECT_ROOT)),
            "sha256": sha256(self.model_path),
            "provider": self.provider,
            "loaded": self.model is not None,
            "error": self.error,
            "output_contract": "TorchScript ([pred, anchor_grid], drivable_logits, lane_logits)",
        }


def lane_quality(mask: np.ndarray) -> float:
    if mask.size == 0:
        return 0.0
    height, width = mask.shape[:2]
    lower = mask[int(height * 0.55) :]
    coverage = float(np.count_nonzero(lower)) / max(lower.size, 1)
    return float(np.clip(coverage * 8.0, 0.0, 1.0))


def neutral_lane_quality(mask: np.ndarray) -> float:
    """A model-agnostic lane coverage proxy used for both adapters."""

    if mask.size == 0:
        return 0.0
    height, width = mask.shape[:2]
    lower = mask[int(height * 0.55) :]
    coverage = float(np.count_nonzero(lower)) / max(lower.size, 1)
    return float(np.clip(coverage * 8.0, 0.0, 1.0))


def mask_iou(left: np.ndarray, right: np.ndarray) -> float:
    left_bool = left.astype(bool)
    right_bool = right.astype(bool)
    union = np.count_nonzero(left_bool | right_bool)
    if union == 0:
        return 1.0
    return float(np.count_nonzero(left_bool & right_bool) / union)


def overlay_lane(frame: np.ndarray, output: dict[str, Any], title: str) -> np.ndarray:
    canvas = frame.copy()
    lane = output["lane_mask"].astype(bool)
    drive = output["drivable_mask"].astype(bool)
    canvas[drive] = (canvas[drive].astype(np.float32) * 0.60 + np.array([40, 140, 40]) * 0.40).astype(np.uint8)
    canvas[lane] = (canvas[lane].astype(np.float32) * 0.40 + np.array([0, 220, 255]) * 0.60).astype(np.uint8)
    cv2.putText(canvas, title, (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)
    return canvas


def add_lane_stats(stats: dict[str, Any], output: dict[str, Any], latency: float) -> None:
    stats["samples"] += 1
    stats["latencies_ms"].append(float(latency))
    stats["qualities"].append(neutral_lane_quality(output["lane_mask"]))
    stats["lane_pixels"].append(int(output.get("lane_pixels", 0)))
    stats["drivable_pixels"].append(
        int(np.count_nonzero(output.get("drivable_mask", np.zeros((1, 1), dtype=np.uint8))))
    )


def finalize_lane_stats(stats: dict[str, Any]) -> dict[str, Any]:
    latencies = stats["latencies_ms"]
    return {
        "samples": int(stats["samples"]),
        "latency_ms": {
            "p50": round(percentile(latencies, 0.50), 3),
            "p95": round(percentile(latencies, 0.95), 3),
            "mean": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        },
        "quality_proxy_mean": round(statistics.fmean(stats["qualities"]), 4) if stats["qualities"] else 0.0,
        "lane_pixels_mean": round(statistics.fmean(stats["lane_pixels"]), 1) if stats["lane_pixels"] else 0.0,
        "drivable_pixels_mean": round(statistics.fmean(stats["drivable_pixels"]), 1) if stats["drivable_pixels"] else 0.0,
        "errors": stats.get("errors", []),
    }


def build_detection_comparison(
    baseline: dict[str, Any], candidate: dict[str, Any], task: str
) -> dict[str, Any]:
    return {
        "frame_detection_rate_delta": round(
            candidate["frame_detection_rate"] - baseline["frame_detection_rate"], 4
        ),
        "detections_per_frame_delta": round(
            candidate["detections_per_frame"] - baseline["detections_per_frame"], 4
        ),
        "latency_p95_ratio": round(
            candidate["latency_ms"]["p95"] / max(baseline["latency_ms"]["p95"], 1e-6), 4
        ),
        "task_note": (
            "Taxonomy is not one-to-one; this is a replay proxy, not accuracy."
            if task == "object"
            else "Candidate has 27 sign classes; production detector has 82 classes; this is not mAP."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark layer1_test model artifacts")
    parser.add_argument("--runtime", choices=["cpu", "directml"], default="cpu")
    parser.add_argument("--samples-per-video", type=int, default=24)
    parser.add_argument("--max-videos", type=int, default=0)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "layer1_test_models_benchmark_20260828.json")
    parser.add_argument("--render-dir", type=Path, default=PROJECT_ROOT / "reports" / "review" / "layer1-test-models")
    args = parser.parse_args()
    if args.samples_per_video < 1:
        raise SystemExit("--samples-per-video must be >= 1")

    from ultralytics import YOLO

    test_root = PROJECT_ROOT / "models" / "layer1_test"
    object_candidate_path = test_root / "BEST_detection_bdd7_ep18.pt"
    sign_candidate_path = test_root / "BEST_signs_vn27_ep21.pt"
    yolopv2_path = test_root / "yolopv2.pt"
    depth_path = test_root / "yolo26s-depth.pt"
    production_object_path = PROJECT_ROOT / "models" / "yolo11n.pt"
    production_sign_path = PROJECT_ROOT / "models" / "roadwatch_detector_v2.pt"
    production_lane_path = PROJECT_ROOT / "models" / "yolop_lane_detection_640.onnx"
    required = [
        object_candidate_path,
        sign_candidate_path,
        yolopv2_path,
        depth_path,
        production_object_path,
        production_sign_path,
        production_lane_path,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing model artifacts: " + ", ".join(missing))

    videos = [PROJECT_ROOT / "media" / name for name in VIDEO_CANDIDATES]
    videos = [path for path in videos if path.exists()]
    if args.max_videos > 0:
        videos = videos[: args.max_videos]
    if not videos:
        raise FileNotFoundError("No representative dashcam videos found")

    object_candidate = YOLO(str(object_candidate_path))
    object_baseline = YOLO(str(production_object_path))
    sign_candidate = YOLO(str(sign_candidate_path))
    sign_baseline = YOLO(str(production_sign_path))
    object_candidate_imgsz = int(object_candidate.overrides.get("imgsz", 960))
    object_baseline_imgsz = int(object_baseline.overrides.get("imgsz", 640))
    sign_candidate_imgsz = int(sign_candidate.overrides.get("imgsz", 1280))
    sign_baseline_imgsz = int(sign_baseline.overrides.get("imgsz", 640))

    lane_baseline = YOLOPSegmenter(
        ConfigManager.model_path("yolop_lane_detection_640.onnx"), args.runtime
    )
    vendor_dir = PROJECT_ROOT.parent / "P-162-develop-sync" / "edge_agent" / "src" / "Layer1" / "vendor" / "YOLOPv2"
    lane_candidate = YoloPv2Lane(yolopv2_path, vendor_dir)

    # One representative frame is used only for warm-up and excluded from metrics.
    first_frame = load_frame(videos[0], video_metadata(videos[0])["duration_s"] * 0.5)
    if first_frame is None:
        raise RuntimeError("Unable to read warm-up frame")
    warmup: dict[str, Any] = {}
    for name, fn in {
        "object_baseline": lambda: run_ultralytics_frame(object_baseline, first_frame, object_baseline_imgsz),
        "object_candidate": lambda: run_ultralytics_frame(object_candidate, first_frame, object_candidate_imgsz),
        "sign_baseline": lambda: run_ultralytics_frame(sign_baseline, first_frame, sign_baseline_imgsz),
        "sign_candidate": lambda: run_ultralytics_frame(sign_candidate, first_frame, sign_candidate_imgsz),
        "lane_baseline": lambda: lane_baseline.infer(first_frame),
        "lane_candidate": lambda: lane_candidate.infer(first_frame),
    }.items():
        started = time.perf_counter()
        fn()
        warmup[name] = round((time.perf_counter() - started) * 1000.0, 3)

    object_stats = {"baseline": new_detection_stats(), "candidate": new_detection_stats()}
    sign_stats = {"baseline": new_detection_stats(), "candidate": new_detection_stats()}
    lane_stats = {
        "baseline": {"samples": 0, "latencies_ms": [], "qualities": [], "lane_pixels": [], "drivable_pixels": [], "errors": []},
        "candidate": {"samples": 0, "latencies_ms": [], "qualities": [], "lane_pixels": [], "drivable_pixels": [], "errors": []},
    }
    rows: list[dict[str, Any]] = []
    read_failures: list[dict[str, Any]] = []
    args.render_dir.mkdir(parents=True, exist_ok=True)

    for video in videos:
        metadata = video_metadata(video)
        timestamps = sample_timestamps(metadata, args.samples_per_video)
        for sample_index, timestamp_s in enumerate(timestamps):
            frame = load_frame(video, timestamp_s)
            if frame is None:
                read_failures.append({"video": video.name, "timestamp_s": timestamp_s})
                continue

            object_baseline_result, object_baseline_ms = run_ultralytics_frame(object_baseline, frame, object_baseline_imgsz)
            object_candidate_result, object_candidate_ms = run_ultralytics_frame(object_candidate, frame, object_candidate_imgsz)
            sign_baseline_result, sign_baseline_ms = run_ultralytics_frame(sign_baseline, frame, sign_baseline_imgsz)
            sign_candidate_result, sign_candidate_ms = run_ultralytics_frame(sign_candidate, frame, sign_candidate_imgsz)
            lane_baseline_result, lane_baseline_ms = lane_baseline.infer(frame)
            lane_candidate_result, lane_candidate_ms = lane_candidate.infer(frame)

            for stats, result, latency in (
                (object_stats["baseline"], object_baseline_result, object_baseline_ms),
                (object_stats["candidate"], object_candidate_result, object_candidate_ms),
                (sign_stats["baseline"], sign_baseline_result, sign_baseline_ms),
                (sign_stats["candidate"], sign_candidate_result, sign_candidate_ms),
            ):
                stats["sampled_frames"] += 1
                stats["latencies_ms"].append(float(latency))
                update_detection_stats(stats, result)
            add_lane_stats(lane_stats["baseline"], lane_baseline_result, lane_baseline_ms)
            add_lane_stats(lane_stats["candidate"], lane_candidate_result, lane_candidate_ms)

            row = {
                "video": video.name,
                "timestamp_s": timestamp_s,
                "sample_index": sample_index,
                "object": {
                    "baseline_detections": len(object_baseline_result.boxes),
                    "candidate_detections": len(object_candidate_result.boxes),
                    "baseline_latency_ms": round(object_baseline_ms, 3),
                    "candidate_latency_ms": round(object_candidate_ms, 3),
                },
                "sign": {
                    "baseline_detections": len(sign_baseline_result.boxes),
                    "candidate_detections": len(sign_candidate_result.boxes),
                    "baseline_latency_ms": round(sign_baseline_ms, 3),
                    "candidate_latency_ms": round(sign_candidate_ms, 3),
                },
                "lane": {
                    "baseline_latency_ms": round(lane_baseline_ms, 3),
                    "candidate_latency_ms": round(lane_candidate_ms, 3),
                    "lane_mask_iou": round(mask_iou(lane_baseline_result["lane_mask"], lane_candidate_result["lane_mask"]), 4),
                    "drivable_mask_iou": round(mask_iou(lane_baseline_result["drivable_mask"], lane_candidate_result["drivable_mask"]), 4),
                },
            }
            rows.append(row)

            if sample_index < 2:
                object_baseline_result.save(filename=str(args.render_dir / f"{video.stem}_{sample_index:02d}_object_baseline.jpg"))
                object_candidate_result.save(filename=str(args.render_dir / f"{video.stem}_{sample_index:02d}_object_candidate.jpg"))
                sign_baseline_result.save(filename=str(args.render_dir / f"{video.stem}_{sample_index:02d}_sign_baseline.jpg"))
                sign_candidate_result.save(filename=str(args.render_dir / f"{video.stem}_{sample_index:02d}_sign_candidate.jpg"))
                cv2.imwrite(str(args.render_dir / f"{video.stem}_{sample_index:02d}_lane_baseline.jpg"), overlay_lane(frame, lane_baseline_result, "YOLOP production"))
                cv2.imwrite(str(args.render_dir / f"{video.stem}_{sample_index:02d}_lane_candidate.jpg"), overlay_lane(frame, lane_candidate_result, "YOLOPv2 candidate"))
        print(f"Completed {video.name}: {len(timestamps)} planned samples", flush=True)

    model_summary = {
        "object": {
            "baseline": finalize_detection_stats(object_stats["baseline"]),
            "candidate": finalize_detection_stats(object_stats["candidate"]),
        },
        "traffic_sign": {
            "baseline": finalize_detection_stats(sign_stats["baseline"]),
            "candidate": finalize_detection_stats(sign_stats["candidate"]),
        },
        "lane": {
            "baseline": finalize_lane_stats(lane_stats["baseline"]),
            "candidate": finalize_lane_stats(lane_stats["candidate"]),
        },
    }
    report = {
        "schema_version": "roadwatch-layer1-test-model-benchmark-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_type": "same-frame-replay-inference-only",
        "production_unchanged": True,
        "runtime": {
            "object_and_sign": "Ultralytics PyTorch CPU",
            "lane_baseline": lane_baseline.status(),
            "lane_candidate": lane_candidate.status(),
            "requested_lane_runtime": args.runtime,
            "note": "PT/TorchScript candidates are CPU-only in this benchmark; no local training.",
        },
        "artifacts": {
            "production": {
                "object": {"file": str(production_object_path.relative_to(PROJECT_ROOT)), "sha256": sha256(production_object_path)},
                "traffic_sign": {"file": str(production_sign_path.relative_to(PROJECT_ROOT)), "sha256": sha256(production_sign_path)},
                "lane": {"file": str(production_lane_path.relative_to(PROJECT_ROOT)), "sha256": sha256(production_lane_path)},
            },
            "candidates": {
                "object": detection_status(object_candidate, object_candidate_path, object_candidate_imgsz),
                "traffic_sign": detection_status(sign_candidate, sign_candidate_path, sign_candidate_imgsz),
                "lane": lane_candidate.status(),
                "depth_auxiliary": {"file": str(depth_path.relative_to(PROJECT_ROOT)), "sha256": sha256(depth_path), "task": "depth", "direct_replacement": False},
            },
        },
        "scope": {
            "videos": [path.name for path in videos],
            "excluded_video": "dashcam_vietnam.mp4",
            "samples_per_video": args.samples_per_video,
            "planned_samples": len(rows) + len(read_failures),
            "processed_samples": len(rows),
            "read_failures": read_failures,
            "ground_truth": False,
            "limitation": "Detection rates, confidence, mask IoU and quality are replay proxies, not precision/recall/mAP or lane accuracy.",
        },
        "warmup_ms": warmup,
        "summary": model_summary,
        "comparisons": {
            "object": build_detection_comparison(model_summary["object"]["baseline"], model_summary["object"]["candidate"], "object"),
            "traffic_sign": build_detection_comparison(model_summary["traffic_sign"]["baseline"], model_summary["traffic_sign"]["candidate"], "traffic_sign"),
            "lane": {
                "lane_latency_p95_ratio": round(model_summary["lane"]["candidate"]["latency_ms"]["p95"] / max(model_summary["lane"]["baseline"]["latency_ms"]["p95"], 1e-6), 4),
                "mean_lane_mask_iou": round(statistics.fmean(row["lane"]["lane_mask_iou"] for row in rows), 4) if rows else 0.0,
                "mean_drivable_mask_iou": round(statistics.fmean(row["lane"]["drivable_mask_iou"] for row in rows), 4) if rows else 0.0,
                "task_note": "Mask agreement is not ground-truth accuracy; candidate needs a lane GT gate before promotion.",
            },
        },
        "decision": {
            "automatic_promotion": False,
            "production_active": {
                "object": "yolo11n",
                "traffic_sign": "roadwatch_detector_v2",
                "lane": "yolop_lane_detection_640",
            },
            "fallback": "All production models remain active; candidates are diagnostic-only.",
            "next_gate": "Review this report and rendered samples, then run task-specific GT/event regression before any promotion.",
        },
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": model_summary, "decision": report["decision"]}, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
