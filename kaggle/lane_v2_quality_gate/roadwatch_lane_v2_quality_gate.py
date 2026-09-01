"""RW-10 Phase 1: target-domain lane candidate generation and quality gate.

This job deliberately does not train. UFLDv2 predictions are unverified candidate
labels; the output is a bounded review package that must pass a human/metric gate
before target-domain fine-tuning is allowed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


INPUT = Path("/kaggle/input")
OUTPUT = Path("/kaggle/working/lane_v2_quality_gate")
FRAME_DIR = OUTPUT / "review_frames"
CONTACT_DIR = OUTPUT / "contact_sheets"
VIDEO_PLAN = {
    "dashcam_vietnam.mp4": ("train", "day", 180),
    "dashcam_vietnam_traffic_multi.mp4": ("train", "dense_traffic", 180),
    "dashcam_vietnam_night.mp4": ("val", "night", 120),
    # Kaggle normalizes the local `rain+night` filename when the dataset is
    # published. Keep the remote filename explicit so missing input fails fast.
    "dashcam_vietnam_rainnight.mp4": ("test", "rain_night", 120),
}
MIN_POINTS = 20


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_onnxruntime():
    try:
        import onnxruntime as ort
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "onnxruntime-gpu>=1.20,<1.24"],
            check=True,
        )
        import onnxruntime as ort
    return ort


def gpu_preflight(ort) -> dict:
    try:
        import torch

        count = torch.cuda.device_count()
        devices = [torch.cuda.get_device_name(i) for i in range(count)]
        torch_version = torch.__version__
    except Exception as exc:
        count, devices, torch_version = 0, [], f"unavailable: {exc}"
    providers = ort.get_available_providers()
    report = {
        "count": count,
        "devices": devices,
        "torch": torch_version,
        "onnxruntime_providers": providers,
    }
    print("GPU preflight:", report, flush=True)
    if count < 1:
        raise RuntimeError("GPU accelerator is mandatory for Lane V2 quality gate")
    if "CUDAExecutionProvider" not in providers:
        raise RuntimeError("ONNX Runtime CUDAExecutionProvider is unavailable")
    return report


def find_unique(name: str) -> Path:
    matches = sorted(INPUT.rglob(name))
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected exactly one {name}, found {len(matches)}")
    return matches[0]


def softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values)
    exp = np.exp(shifted)
    return exp / max(float(np.sum(exp)), 1e-9)


def decode(outputs: dict[str, np.ndarray], width: int, height: int) -> list[dict]:
    loc_row, loc_col = outputs["loc_row"], outputs["loc_col"]
    exist_row, exist_col = outputs["exist_row"], outputs["exist_col"]
    num_grid_row, num_cls_row, _ = loc_row.shape[1:]
    num_grid_col, num_cls_col, _ = loc_col.shape[1:]
    row_anchor = np.linspace(0.42, 1.0, num_cls_row)
    col_anchor = np.linspace(0.0, 1.0, num_cls_col)
    valid_row = np.argmax(exist_row, axis=1)[0]
    valid_col = np.argmax(exist_col, axis=1)[0]
    max_row = np.argmax(loc_row, axis=1)[0]
    max_col = np.argmax(loc_col, axis=1)[0]
    lanes = []
    for lane_id in (1, 2):
        points = []
        if int(np.sum(valid_row[:, lane_id])) > num_cls_row / 2:
            for anchor_id in range(num_cls_row):
                if not valid_row[anchor_id, lane_id]:
                    continue
                center = int(max_row[anchor_id, lane_id])
                indexes = np.arange(max(0, center - 1), min(num_grid_row - 1, center + 1) + 1)
                position = float(np.sum(softmax(loc_row[0, indexes, anchor_id, lane_id]) * indexes) + 0.5)
                points.append([round(position / (num_grid_row - 1) * width), round(row_anchor[anchor_id] * height)])
        lanes.append({"lane_id": lane_id, "role": "ego_boundary", "points": points})
    for lane_id in (0, 3):
        points = []
        if int(np.sum(valid_col[:, lane_id])) > num_cls_col / 4:
            for anchor_id in range(num_cls_col):
                if not valid_col[anchor_id, lane_id]:
                    continue
                center = int(max_col[anchor_id, lane_id])
                indexes = np.arange(max(0, center - 1), min(num_grid_col - 1, center + 1) + 1)
                position = float(np.sum(softmax(loc_col[0, indexes, anchor_id, lane_id]) * indexes) + 0.5)
                points.append([round(col_anchor[anchor_id] * width), round(position / (num_grid_col - 1) * height)])
        lanes.append({"lane_id": lane_id, "role": "side_boundary", "points": points})
    return lanes


def bottom_x(points: list[list[int]]) -> float | None:
    if len(points) < MIN_POINTS:
        return None
    tail = sorted(points, key=lambda p: p[1], reverse=True)[:5]
    return float(np.median([p[0] for p in tail]))


def validate_geometry(lanes: list[dict], width: int) -> tuple[bool, list[str], dict]:
    reasons = []
    ego = [lane for lane in lanes if lane["role"] == "ego_boundary"]
    left = bottom_x(ego[0]["points"]) if len(ego) > 0 else None
    right = bottom_x(ego[1]["points"]) if len(ego) > 1 else None
    if left is None or right is None:
        reasons.append("missing_ego_boundary")
    lane_width_ratio = None
    center_offset = None
    if left is not None and right is not None:
        lane_width_ratio = (right - left) / width
        center_offset = ((left + right) / 2 - width / 2) / width
        if left >= right:
            reasons.append("crossed_ego_boundaries")
        if not 0.12 <= lane_width_ratio <= 0.85:
            reasons.append("implausible_lane_width")
        if abs(center_offset) > 0.28:
            reasons.append("implausible_ego_center")
    return not reasons, reasons, {
        "left_bottom_x": left,
        "right_bottom_x": right,
        "lane_width_ratio": lane_width_ratio,
        "center_offset_normalized": center_offset,
    }


def draw(frame: np.ndarray, lanes: list[dict], accepted: bool, label: str) -> np.ndarray:
    canvas = frame.copy()
    palette = [(255, 180, 0), (0, 255, 0), (0, 220, 255), (255, 80, 180)]
    for lane in lanes:
        points = np.asarray(lane["points"], dtype=np.int32)
        if len(points) >= 2:
            cv2.polylines(canvas, [points], False, palette[lane["lane_id"]], 3)
    color = (30, 200, 30) if accepted else (20, 20, 230)
    cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 42), (0, 0, 0), -1)
    cv2.putText(canvas, label, (12, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.72, color, 2, cv2.LINE_AA)
    return canvas


def read_frame_with_ffmpeg(video: Path, timestamp_s: float) -> np.ndarray | None:
    """Decode one frame when OpenCV cannot seek a target-domain MP4."""
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp_s:.3f}",
        "-i", str(video), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, timeout=45)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    if not result.stdout:
        return None
    try:
        image = cv2.imdecode(np.frombuffer(result.stdout, dtype=np.uint8), cv2.IMREAD_COLOR)
    except cv2.error:
        return None
    return image if image is not None and image.size else None


def make_contact_sheets(records: list[dict]) -> None:
    CONTACT_DIR.mkdir(parents=True, exist_ok=True)
    for condition in sorted({item["condition"] for item in records}):
        selected = [item for item in records if item["condition"] == condition][:24]
        thumbs = []
        for item in selected:
            image = cv2.imread(str(FRAME_DIR / item["review_image"]))
            if image is not None:
                thumbs.append(cv2.resize(image, (480, 270)))
        if not thumbs:
            continue
        rows = []
        blank = np.zeros_like(thumbs[0])
        for start in range(0, len(thumbs), 4):
            row = thumbs[start : start + 4]
            row += [blank] * (4 - len(row))
            rows.append(np.hstack(row))
        cv2.imwrite(str(CONTACT_DIR / f"{condition}.jpg"), np.vstack(rows))


def sample_video(session, video: Path, split: str, condition: str, sample_count: int) -> list[dict]:
    cap = cv2.VideoCapture(str(video))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    if frame_count <= 0:
        raise RuntimeError(f"Cannot read frame count: {video}")
    indexes = np.linspace(0, frame_count - 1, sample_count, dtype=np.int64)
    input_name = session.get_inputs()[0].name
    output_names = [item.name for item in session.get_outputs()]
    records = []
    previous_center = None
    for sequence, frame_index in enumerate(indexes):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
        ok, frame = cap.read()
        if not ok or frame is None:
            frame = read_frame_with_ffmpeg(video, float(frame_index) / fps)
            ok = frame is not None
        if not ok:
            continue
        height, width = frame.shape[:2]
        resized = cv2.resize(frame, (1600, round(320 / 0.6)), interpolation=cv2.INTER_LINEAR)
        crop = resized[-320:, :, :]
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        tensor = ((rgb - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32))
        tensor = np.transpose(tensor, (2, 0, 1))[None].astype(np.float32)
        started = time.perf_counter()
        raw = session.run(None, {input_name: tensor})
        inference_ms = (time.perf_counter() - started) * 1000
        lanes = decode(dict(zip(output_names, raw)), width, height)
        accepted, reasons, geometry = validate_geometry(lanes, width)
        center = geometry["center_offset_normalized"]
        if accepted and previous_center is not None and center is not None and abs(center - previous_center) > 0.16:
            accepted = False
            reasons.append("temporal_center_jump")
        if accepted and center is not None:
            previous_center = center
        record_id = f"{video.stem}-{sequence:04d}"
        review_name = f"{record_id}.jpg"
        annotated = draw(frame, lanes, accepted, f"{record_id} | {'CANDIDATE' if accepted else 'REJECT'}")
        cv2.imwrite(str(FRAME_DIR / review_name), annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
        records.append({
            "id": record_id,
            "source": video.name,
            "split": split,
            "condition": condition,
            "timestamp_s": round(float(frame_index) / fps, 3),
            "frame_index": int(frame_index),
            "label_status": "candidate_unverified" if accepted else "rejected_by_geometry",
            "accepted": accepted,
            "rejection_reasons": reasons,
            "lane_instances": lanes,
            "geometry": geometry,
            "inference_ms": round(inference_ms, 3),
            "review_image": review_name,
        })
    cap.release()
    return records


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    FRAME_DIR.mkdir(parents=True, exist_ok=True)
    status = {"schema_version": 1, "task_id": "RW-10", "started_at": utc_now(), "status": "running"}
    try:
        ort = ensure_onnxruntime()
        status["gpu"] = gpu_preflight(ort)
        model = find_unique("ufldv2_culane_res18_320x1600.onnx")
        status["model"] = {"name": model.name, "bytes": model.stat().st_size, "sha256": sha256(model)}
        videos = {name: find_unique(name) for name in VIDEO_PLAN}
        options = ort.SessionOptions()
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session = ort.InferenceSession(str(model), sess_options=options, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
        if session.get_providers()[0] != "CUDAExecutionProvider":
            raise RuntimeError(f"Unexpected provider order: {session.get_providers()}")
        records = []
        for name, (split, condition, count) in VIDEO_PLAN.items():
            source_records = sample_video(session, videos[name], split, condition, count)
            if not source_records:
                raise RuntimeError(f"Required source produced zero decodable frames: {name}")
            records.extend(source_records)
        make_contact_sheets(records)
        accepted = [item for item in records if item["accepted"]]
        rejection_reasons = Counter(reason for item in records for reason in item["rejection_reasons"])
        latencies = sorted(item["inference_ms"] for item in records)
        p95_index = max(0, math.ceil(0.95 * len(latencies)) - 1)
        split_sources = {split: sorted({r["source"] for r in records if r["split"] == split}) for split in ("train", "val", "test")}
        overlap = bool(set(split_sources["train"]) & set(split_sources["val"]) or set(split_sources["train"]) & set(split_sources["test"]) or set(split_sources["val"]) & set(split_sources["test"]))
        machine_gates = {
            "sample_count_at_least_600": len(records) >= 600,
            "all_required_conditions_present": set(VIDEO_PLAN) <= {r["source"] for r in records},
            "source_group_split_no_overlap": not overlap,
            "candidate_coverage_at_least_050": len(accepted) / max(len(records), 1) >= 0.50,
            "night_candidates_at_least_40": sum(r["accepted"] and r["condition"] == "night" for r in records) >= 40,
            "rain_night_candidates_at_least_40": sum(r["accepted"] and r["condition"] == "rain_night" for r in records) >= 40,
        }
        manifest = {
            "schema_version": 1,
            "task_id": "RW-10",
            "generated_at": utc_now(),
            "label_policy": "UFLDv2 output is candidate_unverified, never verified ground truth",
            "split_sources": split_sources,
            "records": records,
        }
        (OUTPUT / "lane_candidates.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        gate = {
            "schema_version": 1,
            "task_id": "RW-10",
            "generated_at": utc_now(),
            "status": "human_review_required" if all(machine_gates.values()) else "machine_gate_failed",
            "training_blocked": True,
            "pilot_review_gate": {
                "verified_polyline_frames_min": 300,
                "purpose": "validate candidate-label policy before scaling annotation",
            },
            "training_unblock_requires": {
                "verified_polyline_frames_min": 3000,
                "double_review_frames_min": 300,
                "review_disagreement_max": 0.05,
                "night_verified_min": 500,
                "rain_night_verified_min": 400,
                "multi_lane_verified_min": 1000,
                "faded_or_missing_marking_verified_min": 400,
            },
            "sampled_frames": len(records),
            "candidate_frames": len(accepted),
            "candidate_coverage": round(len(accepted) / max(len(records), 1), 4),
            "condition_counts": dict(Counter(r["condition"] for r in records)),
            "accepted_condition_counts": dict(Counter(r["condition"] for r in accepted)),
            "rejection_reasons": dict(rejection_reasons),
            "inference_ms": {"mean": round(float(np.mean(latencies)), 3), "p95": round(latencies[p95_index], 3)},
            "machine_gates": machine_gates,
            "human_gate": "pending",
        }
        (OUTPUT / "quality_gate.json").write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
        status.update({"status": gate["status"], "training_blocked": True, "completed_at": utc_now(), "quality_gate": gate})
    except Exception as exc:
        status.update({"status": "error", "type": type(exc).__name__, "message": str(exc), "completed_at": utc_now()})
        print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)
        (OUTPUT / "job_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
    (OUTPUT / "job_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
