from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "third_party" / "twinlitenetplus"))

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.perception import YOLOPSegmenter  # noqa: E402


DEFAULT_SAMPLES: dict[str, list[float]] = {
    "test_video1.mp4": [10, 14, 18, 28, 32, 36],
    "video_test.mp4": [10, 13, 16, 20, 42, 48, 54],
    "test_video10.mp4": [2, 4, 6, 8],
    "test_video11.mp4": [30, 32, 34, 36],
    "dashcam_vietnam_night.mp4": [15, 45, 75, 105, 135, 165],
    "dashcam_vietnam_rain+night.mp4": [10, 30, 50, 70, 90, 105],
    "dashcam_vietnam_traffic_multi.mp4": [30, 120, 210, 300, 390, 480, 570, 660],
}


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * ratio))]


def mask_iou(left: np.ndarray, right: np.ndarray) -> float:
    left_bool = left.astype(bool)
    right_bool = right.astype(bool)
    union = np.logical_or(left_bool, right_bool).sum()
    if union == 0:
        return 1.0
    return float(np.logical_and(left_bool, right_bool).sum() / union)


def lane_quality(lane: np.ndarray) -> float:
    height, width = lane.shape[:2]
    lower_lane_pixels = int(np.count_nonzero(lane[int(height * 0.45) :]))
    return float(min(1.0, lower_lane_pixels / max(width * height * 0.008, 1)))


def overlay_masks(frame: np.ndarray, output: dict[str, Any], label: str) -> np.ndarray:
    rendered = frame.copy()
    drivable = output["drivable_mask"].astype(bool)
    lane = output["lane_mask"].astype(bool)
    tint = np.zeros_like(frame)
    tint[drivable] = (0, 150, 0)
    tint[lane] = (0, 220, 255)
    visible = drivable | lane
    if np.any(visible):
        rendered[visible] = cv2.addWeighted(
            rendered[visible], 0.60, tint[visible], 0.40, 0.0
        )
    cv2.putText(
        rendered,
        label,
        (24, 42),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return rendered


def letterbox_for_img(
    image: np.ndarray,
    new_shape: int = 640,
    color: tuple[int, int, int] = (114, 114, 114),
) -> tuple[np.ndarray, tuple[float, float], tuple[float, float]]:
    """Use the upstream TwinLiteNet+ demo preprocessing for the candidate."""
    shape = image.shape[:2]
    target = (new_shape, new_shape)
    ratio = min(target[0] / shape[0], target[1] / shape[1])
    new_unpad = int(round(shape[1] * ratio)), int(round(shape[0] * ratio))
    dw = target[1] - new_unpad[0]
    dh = target[0] - new_unpad[1]
    dw, dh = np.mod(dw, 32), np.mod(dh, 32)
    dw /= 2
    dh /= 2
    if shape[::-1] != new_unpad:
        image = cv2.resize(image, new_unpad, interpolation=cv2.INTER_AREA)
    top = int(round(dh - 0.1))
    bottom = int(round(dh + 0.1))
    left = int(round(dw - 0.1))
    right = int(round(dw + 0.1))
    image = cv2.copyMakeBorder(
        image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
    )
    return image, (ratio, ratio), (dw, dh)


class TwinLiteNetPlusSegmenter:
    """Evaluation-only PyTorch adapter for the upstream TwinLiteNet+ checkpoint."""

    def __init__(self, checkpoint: Path, config: str = "medium", device: str = "cpu") -> None:
        import torch
        from model.model import TwinLiteNetPlus

        self.checkpoint = checkpoint
        self.config = config
        self.device_name = device
        self.error: str | None = None
        self.provider = f"torch:{device}"
        self.torch = torch
        self.device = torch.device(device)
        self.model = TwinLiteNetPlus(Namespace(config=config))
        state = torch.load(checkpoint, map_location=self.device, weights_only=False)
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()
        self.parameter_count = int(sum(parameter.numel() for parameter in self.model.parameters()))

    def warmup(self, frame: np.ndarray, count: int = 2) -> float:
        started = time.perf_counter()
        for _ in range(count):
            self.infer(frame)
        return (time.perf_counter() - started) * 1000

    def infer(self, frame: np.ndarray) -> tuple[dict[str, Any], float]:
        started = time.perf_counter()
        height, width = frame.shape[:2]
        padded, _, pad = letterbox_for_img(frame, 640)
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        tensor = np.transpose(rgb, (2, 0, 1)).copy()
        tensor = self.torch.from_numpy(tensor).float().unsqueeze(0).to(self.device) / 255.0
        try:
            with self.torch.inference_mode():
                drive_logits, lane_logits = self.model(tensor)
            drive = drive_logits.argmax(dim=1).squeeze(0).cpu().numpy().astype(np.uint8)
            lane = lane_logits.argmax(dim=1).squeeze(0).cpu().numpy().astype(np.uint8)
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
            "model": self.checkpoint.name,
            "available": self.checkpoint.exists(),
            "loaded": self.model is not None,
            "provider": self.provider,
            "parameters": self.parameter_count,
            "error": self.error,
        }


def load_frame(video_path: Path, timestamp: float) -> np.ndarray | None:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        return None
    capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
    ok, frame = capture.read()
    capture.release()
    return frame if ok else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay TwinLiteNet+ Medium against the RoadWatch YOLOP baseline."
    )
    parser.add_argument(
        "--checkpoint",
        default=str(PROJECT_ROOT / "models" / "twinlitenetplus_medium.pth"),
    )
    parser.add_argument("--runtime", default="cpu", choices=["cpu", "directml", "cuda"])
    parser.add_argument("--output", default="reports/twinlitenetplus_medium_vs_yolop.json")
    parser.add_argument("--render-dir", default="reports/review/twinlitenetplus-vs-yolop")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--torch-threads", type=int, default=0)
    args = parser.parse_args()

    if args.runtime != "cpu":
        raise SystemExit(
            "TwinLiteNet+ evaluation currently uses PyTorch CPU. Use --runtime cpu "
            "for a fair CPU replay; DirectML/CUDA adapter is intentionally not inferred."
        )
    checkpoint = Path(args.checkpoint).resolve()
    if not checkpoint.exists():
        raise FileNotFoundError(checkpoint)
    if args.torch_threads > 0:
        import torch

        torch.set_num_threads(args.torch_threads)

    yolop = YOLOPSegmenter(ConfigManager.model_path("yolop_lane_detection_640.onnx"), args.runtime)
    twin = TwinLiteNetPlusSegmenter(checkpoint)
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
    warmups["twinlitenetplus_medium_ms"] = round(twin.warmup(first_frame, count=2), 3)

    rows: list[dict[str, Any]] = []
    sample_index = 0
    for video_name, timestamps in DEFAULT_SAMPLES.items():
        video_path = PROJECT_ROOT / "media" / video_name
        previous: dict[str, np.ndarray] = {}
        if not video_path.exists():
            rows.append({"video": video_name, "error": "missing_video"})
            continue
        for timestamp in timestamps:
            if args.max_samples and sample_index >= args.max_samples:
                break
            frame = load_frame(video_path, timestamp)
            if frame is None:
                rows.append({"video": video_name, "timestamp": timestamp, "error": "read_failed"})
                continue
            sample_index += 1
            outputs = {
                "yolop": yolop.infer(frame),
                "twinlitenetplus_medium": twin.infer(frame),
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
    for model_name in ("yolop", "twinlitenetplus_medium"):
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
        "benchmark_scope": "same RoadWatch replay frames; no frame-level ground truth",
        "preprocessing": {
            "yolop": "RoadWatch adapter: direct 640x640 resize + RGB ImageNet normalization",
            "twinlitenetplus_medium": "upstream-style letterbox to 640, RGB, /255.0, unpad to source frame",
        },
        "checkpoint": str(checkpoint),
        "models": {"yolop": yolop.status(), "twinlitenetplus_medium": twin.status()},
        "warmup_ms": warmups,
        "samples": rows,
        "aggregates": aggregates,
        "limitations": [
            "No lane/drivable-area ground truth is attached to these dashcam frames; IoU and lane-count accuracy cannot be claimed.",
            "Temporal IoU is a diagnostic across selected timestamps, not a substitute for contiguous-frame stability testing.",
            "Published TwinLiteNet+ metrics come from its benchmark protocol and are not direct RoadWatch measurements.",
        ],
        "gate": {
            "default_profile": "yolop",
            "candidate_profile": "twinlitenetplus_medium",
            "automatically_promoted": False,
            "promotion_rule": "Requires labeled lane gate, multi-lane/LDW event regression, and edge runtime benchmark; this replay alone never promotes a model.",
        },
    }
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"aggregates": aggregates, "output": str(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
