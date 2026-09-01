from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.perception import YOLOPSegmenter  # noqa: E402
from benchmark_twinlitenetplus_vs_yolop import (  # noqa: E402
    DEFAULT_SAMPLES,
    lane_quality,
    letterbox_for_img,
    load_frame,
    mask_iou,
    overlay_masks,
    percentile,
)


class TwinLiteNetPlusOnnxSegmenter:
    """ONNX Runtime adapter for the static-shape TwinLiteNet+ export."""

    def __init__(self, model_path: Path, runtime: str = "cpu") -> None:
        import onnxruntime as ort

        self.model_path = model_path
        self.runtime = runtime
        self.error: str | None = None
        available = ort.get_available_providers()
        if runtime == "directml":
            if "DmlExecutionProvider" not in available:
                raise RuntimeError(f"DmlExecutionProvider unavailable; found {available}")
            providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
        elif runtime == "cuda":
            if "CUDAExecutionProvider" not in available:
                raise RuntimeError(f"CUDAExecutionProvider unavailable; found {available}")
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        else:
            providers = ["CPUExecutionProvider"]
        self.session = ort.InferenceSession(
            str(model_path), providers=providers
        )
        input_meta = self.session.get_inputs()[0]
        self.input_name = input_meta.name
        input_shape = list(input_meta.shape)
        if any(not isinstance(value, int) for value in input_shape):
            raise ValueError(f"Expected static ONNX input shape, got {input_shape}")
        if len(input_shape) != 4 or input_shape[0] != 1 or input_shape[1] != 3:
            raise ValueError(f"Unsupported ONNX input shape: {input_shape}")
        self.input_height = int(input_shape[2])
        self.input_width = int(input_shape[3])
        self.provider = self.session.get_providers()[0]

    def warmup(self, frame: np.ndarray, count: int = 2) -> float:
        started = time.perf_counter()
        for _ in range(count):
            self.infer(frame)
        return (time.perf_counter() - started) * 1000

    def infer(self, frame: np.ndarray) -> tuple[dict[str, Any], float]:
        started = time.perf_counter()
        height, width = frame.shape[:2]
        padded, _, pad = letterbox_for_img(frame, 640)
        if padded.shape[:2] != (self.input_height, self.input_width):
            raise ValueError(
                "Static TwinLiteNet+ export expects "
                f"{self.input_width}x{self.input_height}, but preprocessing produced "
                f"{padded.shape[1]}x{padded.shape[0]}"
            )
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        tensor = np.transpose(rgb, (2, 0, 1))[None].astype(np.float32)
        try:
            drive_logits, lane_logits = self.session.run(None, {self.input_name: tensor})
            drive = np.argmax(drive_logits[0], axis=0).astype(np.uint8)
            lane = np.argmax(lane_logits[0], axis=0).astype(np.uint8)
            pad_w, pad_h = int(round(pad[0])), int(round(pad[1]))
            out_height, out_width = drive.shape[:2]
            drive = drive[pad_h : out_height - pad_h, pad_w : out_width - pad_w]
            lane = lane[pad_h : out_height - pad_h, pad_w : out_width - pad_w]
            drive = cv2.resize(drive, (width, height), interpolation=cv2.INTER_NEAREST)
            lane = cv2.resize(lane, (width, height), interpolation=cv2.INTER_NEAREST)
            return {
                "lane_mask": lane,
                "drivable_mask": drive,
                "quality": round(lane_quality(lane), 4),
                "lane_pixels": int(np.count_nonzero(lane)),
                "drivable_pixels": int(np.count_nonzero(drive)),
                "provider": self.provider,
            }, (time.perf_counter() - started) * 1000
        except Exception as exc:  # pragma: no cover - runtime dependent
            self.error = str(exc)
            return {
                "lane_mask": np.zeros((height, width), dtype=np.uint8),
                "drivable_mask": np.zeros((height, width), dtype=np.uint8),
                "quality": 0.0,
                "lane_pixels": 0,
                "drivable_pixels": 0,
                "provider": self.provider,
            }, (time.perf_counter() - started) * 1000

    def status(self) -> dict[str, Any]:
        return {
            "model": self.model_path.name,
            "available": self.model_path.exists(),
            "loaded": self.session is not None,
            "provider": self.provider,
            "input_shape": [1, 3, self.input_height, self.input_width],
            "error": self.error,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare static ONNX TwinLiteNet+ Medium with RoadWatch YOLOP."
    )
    parser.add_argument(
        "--checkpoint",
        default=str(PROJECT_ROOT / "models" / "twinlitenetplus_medium.onnx"),
    )
    parser.add_argument("--runtime", default="cpu", choices=["cpu", "directml", "cuda"])
    parser.add_argument("--output", default="reports/twinlitenetplus_medium_onnx_vs_yolop.json")
    parser.add_argument("--render-dir", default="reports/review/twinlitenetplus-onnx-vs-yolop")
    parser.add_argument("--max-samples", type=int, default=0)
    args = parser.parse_args()

    checkpoint = Path(args.checkpoint).resolve()
    if not checkpoint.exists():
        raise FileNotFoundError(checkpoint)
    yolop = YOLOPSegmenter(ConfigManager.model_path("yolop_lane_detection_640.onnx"), args.runtime)
    twin = TwinLiteNetPlusOnnxSegmenter(checkpoint, args.runtime)
    render_dir = PROJECT_ROOT / args.render_dir
    render_dir.mkdir(parents=True, exist_ok=True)

    first_frame = None
    for video_name, timestamps in DEFAULT_SAMPLES.items():
        for timestamp in timestamps:
            first_frame = load_frame(PROJECT_ROOT / "media" / video_name, timestamp)
            if first_frame is not None:
                break
        if first_frame is not None:
            break
    if first_frame is None:
        raise RuntimeError("No benchmark frame could be read from roadwatch/media")

    warmup_started = time.perf_counter()
    for _ in range(2):
        yolop.infer(first_frame)
    warmups = {"yolop_ms": round((time.perf_counter() - warmup_started) * 1000, 3)}
    warmups["twinlitenetplus_medium_onnx_ms"] = round(twin.warmup(first_frame, count=2), 3)

    rows: list[dict[str, Any]] = []
    sample_index = 0
    for video_name, timestamps in DEFAULT_SAMPLES.items():
        previous: dict[str, np.ndarray] = {}
        video_path = PROJECT_ROOT / "media" / video_name
        if not video_path.exists():
            rows.append({"video": video_name, "error": "missing_video"})
            continue
        for timestamp in timestamps:
            if args.max_samples and sample_index >= args.max_samples:
                break
            frame = load_frame(video_path, timestamp)
            if frame is None:
                rows.append({"video": video_name, "timestamp_s": timestamp, "error": "read_failed"})
                continue
            sample_index += 1
            outputs = {
                "yolop": yolop.infer(frame),
                "twinlitenetplus_medium_onnx": twin.infer(frame),
            }
            for model_name, (output, latency) in outputs.items():
                temporal_iou = None
                if model_name in previous:
                    temporal_iou = mask_iou(previous[model_name], output["lane_mask"])
                previous[model_name] = output["lane_mask"]
                row = {
                    "video": video_name,
                    "timestamp_s": timestamp,
                    "model": model_name,
                    "quality": float(output.get("quality", 0.0)),
                    "lane_pixels": int(output.get("lane_pixels", 0)),
                    "drivable_pixels": int(
                        output.get("drivable_pixels", np.count_nonzero(output["drivable_mask"]))
                    ),
                    "latency_ms": round(float(latency), 3),
                    "temporal_lane_mask_iou_to_previous_sample": (
                        round(float(temporal_iou), 4) if temporal_iou is not None else None
                    ),
                    "provider": output.get("provider", "unknown"),
                }
                rows.append(row)
                if timestamp in timestamps[:2]:
                    rendered = overlay_masks(
                        frame,
                        output,
                        f"{model_name} q={row['quality']:.2f} t={row['latency_ms']:.1f}ms",
                    )
                    cv2.imwrite(
                        str(render_dir / f"{Path(video_name).stem}_{timestamp:05.1f}_{model_name}.jpg"),
                        rendered,
                        [cv2.IMWRITE_JPEG_QUALITY, 88],
                    )
        if args.max_samples and sample_index >= args.max_samples:
            break

    aggregates: dict[str, dict[str, Any]] = {}
    for model_name in ("yolop", "twinlitenetplus_medium_onnx"):
        selected = [row for row in rows if row.get("model") == model_name]
        latencies = [float(row["latency_ms"]) for row in selected]
        qualities = [float(row["quality"]) for row in selected]
        temporal = [
            float(row["temporal_lane_mask_iou_to_previous_sample"])
            for row in selected
            if row.get("temporal_lane_mask_iou_to_previous_sample") is not None
        ]
        aggregates[model_name] = {
            "samples": len(selected),
            "latency_p50_ms": round(percentile(latencies, 0.50), 3),
            "latency_p95_ms": round(percentile(latencies, 0.95), 3),
            "latency_mean_ms": round(statistics.fmean(latencies), 3) if latencies else 0.0,
            "mean_quality": round(statistics.fmean(qualities), 4) if qualities else 0.0,
            "mean_temporal_lane_mask_iou": round(statistics.fmean(temporal), 4) if temporal else None,
        }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_scope": f"same RoadWatch replay frames; static ONNX candidate; runtime={args.runtime}; no frame-level ground truth",
        "preprocessing": {
            "yolop": "RoadWatch adapter: direct 640x640 resize + RGB ImageNet normalization",
            "twinlitenetplus_medium_onnx": "upstream-style letterbox to 640x384, RGB, /255.0, unpad to source frame",
        },
        "checkpoint": str(checkpoint),
        "models": {"yolop": yolop.status(), "twinlitenetplus_medium_onnx": twin.status()},
        "warmup_ms": warmups,
        "samples": rows,
        "aggregates": aggregates,
        "limitations": [
            "No lane/drivable-area ground truth is attached to these dashcam frames; IoU and lane-count accuracy cannot be claimed.",
            "Temporal IoU is a diagnostic across selected timestamps, not a substitute for contiguous-frame stability testing.",
            "This benchmark does not represent Jetson TensorRT performance.",
        ],
        "gate": {
            "default_profile": "yolop",
            "candidate_profile": "twinlitenetplus_medium_onnx",
            "automatically_promoted": False,
            "promotion_rule": "Requires labeled lane gate, multi-lane/LDW event regression, and target-edge benchmark; this replay alone never promotes a model.",
        },
    }
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"aggregates": aggregates, "output": str(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
