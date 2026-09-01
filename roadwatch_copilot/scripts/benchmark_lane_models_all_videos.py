from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from benchmark_twinlitenetplus_onnx_vs_yolop import (  # noqa: E402
    TwinLiteNetPlusOnnxSegmenter,
    lane_quality,
    load_frame,
    mask_iou,
    overlay_masks,
    percentile,
)
from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.perception import YOLOPSegmenter  # noqa: E402


MODEL_NAMES = ("yolop", "twinlitenetplus_medium_onnx")


def video_metadata(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return {"fps": 0.0, "frames": 0, "duration_s": 0.0, "width": 0, "height": 0}
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    metadata = {
        "fps": round(fps, 4),
        "frames": frames,
        "duration_s": round(frames / fps, 3) if fps > 0 else 0.0,
        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
    }
    capture.release()
    return metadata


def sample_timestamps(metadata: dict[str, Any], count: int) -> list[float]:
    duration = float(metadata.get("duration_s") or 0.0)
    if duration <= 0.0:
        return []
    # Avoid the first/last GOP boundary; the same deterministic timestamps go to both models.
    fractions = np.linspace(0.08, 0.92, max(1, count))
    return [round(float(duration * fraction), 3) for fraction in fractions]


def summary_for(rows: list[dict[str, Any]], model_name: str) -> dict[str, Any]:
    selected = [row[model_name] for row in rows if model_name in row]
    latencies = [float(item["latency_ms"]) for item in selected]
    qualities = [float(item["quality"]) for item in selected]
    temporal = [
        float(item["temporal_lane_mask_iou_to_previous_sample"])
        for item in selected
        if item.get("temporal_lane_mask_iou_to_previous_sample") is not None
    ]
    return {
        "samples": len(selected),
        "latency_p50_ms": round(percentile(latencies, 0.50), 3),
        "latency_p95_ms": round(percentile(latencies, 0.95), 3),
        "latency_mean_ms": round(statistics.fmean(latencies), 3) if latencies else 0.0,
        "mean_quality_proxy": round(statistics.fmean(qualities), 4) if qualities else 0.0,
        "mean_temporal_lane_mask_iou": round(statistics.fmean(temporal), 4) if temporal else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay YOLOP and TwinLiteNet+ on every RoadWatch media video."
    )
    parser.add_argument("--video-dir", type=Path, default=PROJECT_ROOT / "media")
    parser.add_argument("--runtime", default="directml", choices=["cpu", "directml", "cuda"])
    parser.add_argument("--samples-per-video", type=int, default=6)
    parser.add_argument("--max-videos", type=int, default=0)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "twinlitenetplus_medium_vs_yolop_all_videos.json",
    )
    parser.add_argument(
        "--render-dir",
        type=Path,
        default=PROJECT_ROOT / "reports" / "review" / "twinlitenetplus-vs-yolop-all-videos",
    )
    args = parser.parse_args()

    if args.samples_per_video < 1:
        raise SystemExit("--samples-per-video must be >= 1")
    video_paths = sorted(args.video_dir.glob("*.mp4"))
    if args.max_videos > 0:
        video_paths = video_paths[: args.max_videos]
    if not video_paths:
        raise SystemExit(f"No .mp4 files found under {args.video_dir}")

    candidate = PROJECT_ROOT / "models" / "twinlitenetplus_medium.onnx"
    if not candidate.exists():
        raise FileNotFoundError(candidate)
    yolop = YOLOPSegmenter(ConfigManager.model_path("yolop_lane_detection_640.onnx"), args.runtime)
    twin = TwinLiteNetPlusOnnxSegmenter(candidate, args.runtime)

    first_frame = None
    metadata_by_video: dict[str, dict[str, Any]] = {}
    sample_plan: dict[str, list[float]] = {}
    for path in video_paths:
        metadata = video_metadata(path)
        metadata_by_video[path.name] = metadata
        sample_plan[path.name] = sample_timestamps(metadata, args.samples_per_video)
        if first_frame is None:
            for timestamp in sample_plan[path.name]:
                first_frame = load_frame(path, timestamp)
                if first_frame is not None:
                    break
    if first_frame is None:
        raise RuntimeError("No readable sample frame found")

    warmup_started = time.perf_counter()
    yolop.infer(first_frame)
    yolop_warmup_ms = (time.perf_counter() - warmup_started) * 1000.0
    twin_warmup_ms = twin.warmup(first_frame, count=1)

    args.render_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    previous: dict[str, dict[str, np.ndarray]] = {}
    processed_samples = 0
    read_failures: list[dict[str, Any]] = []

    for video_path in video_paths:
        previous[video_path.name] = {}
        for sample_idx, timestamp in enumerate(sample_plan[video_path.name]):
            if args.max_samples > 0 and processed_samples >= args.max_samples:
                break
            frame = load_frame(video_path, timestamp)
            if frame is None:
                read_failures.append({"video": video_path.name, "timestamp_s": timestamp})
                continue
            processed_samples += 1
            outputs = {
                "yolop": yolop.infer(frame),
                "twinlitenetplus_medium_onnx": twin.infer(frame),
            }
            row: dict[str, Any] = {
                "video": video_path.name,
                "timestamp_s": timestamp,
                "sample_index": sample_idx,
            }
            masks: dict[str, dict[str, np.ndarray]] = {}
            for model_name, (output, latency) in outputs.items():
                mask = output["lane_mask"]
                temporal = None
                if model_name in previous[video_path.name]:
                    temporal = mask_iou(previous[video_path.name][model_name], mask)
                previous[video_path.name][model_name] = mask
                masks[model_name] = output
                row[model_name] = {
                    "quality": float(output.get("quality", lane_quality(mask))),
                    "lane_pixels": int(output.get("lane_pixels", np.count_nonzero(mask))),
                    "drivable_pixels": int(output.get("drivable_pixels", np.count_nonzero(output["drivable_mask"]))),
                    "latency_ms": round(float(latency), 3),
                    "temporal_lane_mask_iou_to_previous_sample": (
                        round(float(temporal), 4) if temporal is not None else None
                    ),
                    "provider": output.get("provider", "unknown"),
                }
            row["lane_mask_iou_between_models"] = round(
                mask_iou(masks["yolop"]["lane_mask"], masks["twinlitenetplus_medium_onnx"]["lane_mask"]),
                4,
            )
            row["drivable_mask_iou_between_models"] = round(
                mask_iou(masks["yolop"]["drivable_mask"], masks["twinlitenetplus_medium_onnx"]["drivable_mask"]),
                4,
            )
            rows.append(row)

            if sample_idx < 2:
                for model_name, output in masks.items():
                    label = (
                        f"{model_name} q={row[model_name]['quality']:.2f} "
                        f"t={row[model_name]['latency_ms']:.1f}ms"
                    )
                    rendered = overlay_masks(frame, output, label)
                    output_name = f"{video_path.stem}_{sample_idx:02d}_{model_name}.jpg"
                    cv2.imwrite(str(args.render_dir / output_name), rendered, [cv2.IMWRITE_JPEG_QUALITY, 88])
        if args.max_samples > 0 and processed_samples >= args.max_samples:
            break

    per_video: dict[str, Any] = {}
    for video_name in metadata_by_video:
        video_rows = [row for row in rows if row.get("video") == video_name]
        if not video_rows:
            continue
        per_video[video_name] = {
            "metadata": metadata_by_video[video_name],
            "planned_timestamps_s": sample_plan[video_name],
            "samples": len(video_rows),
            "yolop": summary_for(video_rows, "yolop"),
            "twinlitenetplus_medium_onnx": summary_for(video_rows, "twinlitenetplus_medium_onnx"),
            "mean_lane_mask_iou_between_models": round(
                statistics.fmean(float(row["lane_mask_iou_between_models"]) for row in video_rows), 4
            ),
            "mean_drivable_mask_iou_between_models": round(
                statistics.fmean(float(row["drivable_mask_iou_between_models"]) for row in video_rows), 4
            ),
        }

    model_summary = {
        model_name: summary_for(rows, model_name)
        for model_name in MODEL_NAMES
    }
    candidate_latency_ratio = None
    baseline_p95 = model_summary["yolop"]["latency_p95_ms"]
    candidate_p95 = model_summary["twinlitenetplus_medium_onnx"]["latency_p95_ms"]
    if baseline_p95 > 0:
        candidate_latency_ratio = round(candidate_p95 / baseline_p95, 4)

    report = {
        "schema_version": "roadwatch-lane-replay-benchmark-v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_scope": "All .mp4 files in roadwatch/media; same deterministic timestamps per video; no lane ground truth",
        "runtime_requested": args.runtime,
        "models": {"yolop": yolop.status(), "twinlitenetplus_medium_onnx": twin.status()},
        "preprocessing": {
            "yolop": "RoadWatch adapter, 640x640 input",
            "twinlitenetplus_medium_onnx": "Static 640x384 export, upstream-style letterbox, RGB /255",
            "fairness_note": "Latency is operationally useful but not strictly resolution-matched because the two deployed adapters use different native input shapes.",
        },
        "sampling": {
            "video_count": len(video_paths),
            "planned_samples_per_video": args.samples_per_video,
            "processed_samples": processed_samples,
            "read_failures": read_failures,
            "videos": [path.name for path in video_paths],
        },
        "video_metadata": metadata_by_video,
        "warmup_ms": {
            "yolop": round(yolop_warmup_ms, 3),
            "twinlitenetplus_medium_onnx": round(float(twin_warmup_ms), 3),
        },
        "models_summary": model_summary,
        "per_video": per_video,
        "samples": rows,
        "decision": {
            "automatically_promoted": False,
            "default_fallback": "yolop",
            "candidate_latency_p95_ratio_vs_yolop": candidate_latency_ratio,
            "quality_proxy_is_not_accuracy": True,
            "required_before_production_switch": [
                "Human-verified lane ground truth",
                "Lane-count and ego-boundary metrics",
                "Night/rain/multi-lane LDW event regression",
                "Target-edge benchmark",
            ],
        },
        "limitations": [
            "Quality proxy measures lower-frame lane pixel occupancy; it is not IoU or semantic accuracy.",
            "Temporal mask IoU uses sparse samples per video, not contiguous frame stability.",
            "No drivable-area ground truth is available, so drivable mIoU cannot be claimed.",
            "This is a replay benchmark on existing videos, not a closed-course safety validation.",
        ],
        "render_dir": str(args.render_dir),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    markdown_path = args.output.with_suffix(".md")
    markdown = [
        "# YOLOP vs TwinLiteNet+ — All RoadWatch Videos Replay",
        "",
        f"Generated: `{report['generated_at']}`  ",
        f"Runtime: `{args.runtime}`  ",
        f"Videos: `{len(video_paths)}`; processed samples: `{processed_samples}`",
        "",
        "> Đây là benchmark replay không có ground-truth. Quality proxy, temporal IoU và mask agreement chỉ dùng để hỗ trợ quyết định demo; không phải accuracy/mIoU.",
        "",
        "## Tổng hợp",
        "",
        "| Model | Samples | P50 (ms) | P95 (ms) | Mean quality proxy | Temporal IoU |\n|---|---:|---:|---:|---:|---:|",
    ]
    for model_name, values in model_summary.items():
        markdown.append(
            f"| `{model_name}` | {values['samples']} | {values['latency_p50_ms']} | {values['latency_p95_ms']} | {values['mean_quality_proxy']} | {values['mean_temporal_lane_mask_iou']} |"
        )
    markdown.extend(
        [
            "",
            "## Quyết định an toàn",
            "",
            "- Không tự động promote model nào.",
            "- YOLOP vẫn là fallback production.",
            "- TwinLiteNet+ chỉ có thể là demo candidate sau khi kiểm tra ảnh overlay; muốn thay production vẫn cần ground-truth và LDW regression.",
            "- Ảnh overlay nằm tại:",
            f"  `{args.render_dir}`",
            "",
            "## Theo từng video",
            "",
        ]
    )
    for video_name, values in per_video.items():
        markdown.append(
            f"- `{video_name}` — {values['samples']} samples; "
            f"YOLOP P95 `{values['yolop']['latency_p95_ms']} ms`; "
            f"TwinLiteNet+ P95 `{values['twinlitenetplus_medium_onnx']['latency_p95_ms']} ms`; "
            f"lane agreement `{values['mean_lane_mask_iou_between_models']}`."
        )
    markdown_path.write_text("\n".join(markdown) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "markdown": str(markdown_path),
                "processed_samples": processed_samples,
                "models_summary": model_summary,
                "read_failures": read_failures,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
