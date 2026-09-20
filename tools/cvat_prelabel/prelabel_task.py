from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROADWATCH_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROADWATCH_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from roadwatch.perception import OnnxYoloDetector, SpeedValueClassifier, TrafficSignEnsemble

from tools.cvat_prelabel.cvat_api import CvatApiError, CvatClient
from tools.cvat_prelabel.evidence import (
    draw_prediction,
    make_contact_sheet,
    sha256_file,
    write_hash_manifest,
    write_json,
)
from tools.cvat_prelabel.taxonomy import canonical_label, cvat_attributes, default_speed_attributes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pre-label a CVAT task with RoadWatch V2 models.")
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--env", type=Path, default=ROADWATCH_ROOT / ".env")
    parser.add_argument("--detector-confidence", type=float, default=0.42)
    parser.add_argument("--speed-confidence", type=float, default=0.95)
    parser.add_argument("--runtime", default="directml")
    parser.add_argument("--max-frames", type=int, default=0, help="0 processes every frame")
    parser.add_argument("--frame-step", type=int, default=1)
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--allow-existing", action="store_true")
    parser.add_argument("--run-name", default="")
    return parser.parse_args()


def decode_frame(data: bytes) -> np.ndarray:
    frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError("CVAT returned an undecodable frame")
    return frame


def build_model(args: argparse.Namespace) -> TrafficSignEnsemble:
    detector = OnnxYoloDetector(
        ROADWATCH_ROOT / "models" / "roadwatch_detector_v2.onnx",
        args.detector_confidence,
        640,
        args.runtime,
        optional_head=True,
    )
    classifier = SpeedValueClassifier(
        ROADWATCH_ROOT / "models" / "roadwatch_speed_digits_v2.onnx",
        args.speed_confidence,
        args.runtime,
    )
    model = TrafficSignEnsemble(detector, classifier)
    model.load()
    status = model.status()
    if not status.get("loaded") or status.get("error"):
        raise RuntimeError(f"RoadWatch sign detector unavailable: {status}")
    classifier_status = status.get("speed_classifier", {})
    if not classifier_status.get("loaded") or classifier_status.get("error"):
        raise RuntimeError(f"RoadWatch speed classifier unavailable: {classifier_status}")
    return model


def main() -> int:
    args = parse_args()
    client = CvatClient(args.env)
    task = client.get_task(args.task_id)
    if int(task.get("project_id") or -1) != args.project_id:
        raise CvatApiError("Task/project mismatch; refusing to annotate")
    project = client.get_project(args.project_id)
    labels = client.get_labels(project_id=args.project_id)
    labels_by_name = {item["name"]: item for item in labels}
    required = {
        "speed_limit_max",
        "speed_limit_end",
        "speed_zone_end",
        "prohibition",
        "mandatory",
        "warning",
        "information",
        "traffic_light",
        "unknown_sign",
        "no_entry",
        "stop",
        "pedestrian_crossing",
        "children_crossing",
        "road_work",
        "slippery_road",
        "accident_area",
        "obstacle",
        "level_crossing",
        "roundabout",
        "sharp_left",
        "sharp_right",
        "red_light",
    }
    missing = sorted(required - labels_by_name.keys())
    if missing:
        raise CvatApiError(f"CVAT schema is missing labels: {missing}")

    before = client.get_annotations(args.task_id)
    existing_count = sum(len(before.get(key, [])) for key in ("tags", "shapes", "tracks"))
    if existing_count and not args.allow_existing:
        raise CvatApiError(
            f"Task already has {existing_count} annotations; rerun with --allow-existing only after backup"
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_name = args.run_name or f"task-{args.task_id}-prelabel-{timestamp}"
    run_dir = ROADWATCH_ROOT / "evaluation" / "cvat" / run_name
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "task.json", task)
    write_json(run_dir / "project.json", project)
    write_json(run_dir / "labels.json", labels)
    write_json(run_dir / "pre_upload_annotations.json", before)

    model = build_model(args)
    model_status = model.status()
    model_paths = [
        ROADWATCH_ROOT / "models" / "roadwatch_detector_v2.onnx",
        ROADWATCH_ROOT / "models" / "roadwatch_speed_digits_v2.onnx",
    ]
    write_json(
        run_dir / "model_manifest.json",
        {
            "models": [
                {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
                for path in model_paths
            ],
            "runtime": args.runtime,
            "detector_confidence": args.detector_confidence,
            "speed_classifier_confidence": args.speed_confidence,
            "status": model_status,
        },
    )

    size = int(task["size"])
    frame_numbers = list(range(0, size, max(1, args.frame_step)))
    if args.max_frames > 0:
        frame_numbers = frame_numbers[: args.max_frames]
    shapes: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    visual_candidates: list[tuple[float, np.ndarray]] = []
    frame_hashes: list[dict[str, Any]] = []
    latencies: list[float] = []
    counts: Counter[str] = Counter()
    started = time.perf_counter()

    for index, frame_number in enumerate(frame_numbers, start=1):
        frame_bytes = client.get_frame(args.task_id, frame_number)
        frame_hashes.append(
            {"frame": frame_number, "sha256": hashlib.sha256(frame_bytes).hexdigest(), "bytes": len(frame_bytes)}
        )
        frame = decode_frame(frame_bytes)
        detections, latency_ms = model.infer(frame)
        latencies.append(latency_ms)
        frame_predictions: list[dict[str, Any]] = []
        for detection in detections:
            speed = detection.get("speed_value")
            if speed is None and str(detection.get("label", "")).isdigit():
                speed = int(detection["label"])
            detector_label = str(detection.get("detector_label") or detection.get("label") or "")
            mapped = canonical_label(detector_label, speed)
            if mapped is None:
                continue
            label_spec = labels_by_name[mapped]
            attributes = (
                cvat_attributes(label_spec, default_speed_attributes(speed))
                if mapped == "speed_limit_max"
                else []
            )
            bbox = [float(value) for value in detection["bbox"]]
            prediction = {
                "frame": frame_number,
                "bbox": bbox,
                "detector_label": detector_label,
                "canonical_label": mapped,
                "confidence": float(detection["confidence"]),
                "speed_value": speed,
                "speed_classifier_confidence": detection.get("speed_classifier_confidence"),
                "attributes": attributes,
            }
            frame_predictions.append(prediction)
            predictions.append(prediction)
            counts[mapped] += 1
            shapes.append(
                {
                    "type": "rectangle",
                    "frame": frame_number,
                    "label_id": int(label_spec["id"]),
                    "group": 0,
                    "source": "auto",
                    "occluded": False,
                    "points": bbox,
                    "z_order": 0,
                    "rotation": 0.0,
                    "attributes": attributes,
                }
            )
        if frame_predictions:
            score = max(item["confidence"] for item in frame_predictions)
            visual_candidates.append((score, draw_prediction(frame, frame_predictions)))
        if index % 25 == 0 or index == len(frame_numbers):
            print(f"Processed {index}/{len(frame_numbers)} frames; detections={len(predictions)}", flush=True)

    duration = time.perf_counter() - started
    payload = {
        "version": int(before.get("version", 0)),
        "tags": list(before.get("tags", [])),
        "shapes": list(before.get("shapes", [])) + shapes,
        "tracks": list(before.get("tracks", [])),
    }
    write_json(run_dir / "frame_manifest.json", frame_hashes)
    with (run_dir / "predictions.jsonl").open("w", encoding="utf-8") as handle:
        for item in predictions:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    write_json(run_dir / "cvat_annotation_payload.json", payload)
    metrics = {
        "status": "dry_run_complete",
        "task_id": args.task_id,
        "project_id": args.project_id,
        "frames_in_task": size,
        "frames_processed": len(frame_numbers),
        "detections": len(predictions),
        "detections_by_label": dict(sorted(counts.items())),
        "duration_seconds": round(duration, 3),
        "frames_per_second": round(len(frame_numbers) / duration, 3) if duration else None,
        "latency_mean_ms": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "upload_requested": bool(args.upload),
    }
    write_json(run_dir / "metrics_prelabel.json", metrics)
    visual_candidates.sort(key=lambda item: item[0], reverse=True)
    make_contact_sheet([item[1] for item in visual_candidates[:24]], run_dir / "contact_sheet.jpg")

    if args.upload:
        client.replace_annotations(args.task_id, payload)
        after = client.get_annotations(args.task_id)
        write_json(run_dir / "post_upload_annotations.json", after)
        server_shapes = len(after.get("shapes", []))
        if server_shapes != len(payload["shapes"]):
            raise CvatApiError(
                f"Upload verification failed: expected {len(payload['shapes'])} shapes, server has {server_shapes}"
            )
        metrics["status"] = "uploaded_and_verified"
        metrics["server_shapes"] = server_shapes
        write_json(run_dir / "metrics_prelabel.json", metrics)

    report = f"""# RoadWatch CVAT Pre-label Evidence

- Run: `{run_name}`
- UTC: `{timestamp}`
- Project: `{project['name']}` (`{args.project_id}`)
- Task: `{task['name']}` (`{args.task_id}`)
- Frames processed: `{len(frame_numbers)}/{size}`
- Predictions: `{len(predictions)}`
- Status: `{metrics['status']}`
- Runtime: `{args.runtime}`
- Detector threshold: `{args.detector_confidence}`
- Speed classifier threshold: `{args.speed_confidence}`

## Evidence contract

This directory is the immutable machine prediction snapshot captured before
human correction. `predictions.jsonl` is the model-level evidence,
`cvat_annotation_payload.json` is the exact upload payload, model hashes lock
the weights, and `hashes.sha256` protects the evidence files. Human-reviewed
annotations must be exported to a separate directory and compared; never edit
this snapshot in place.
"""
    (run_dir / "REPORT.md").write_text(report, encoding="utf-8")
    write_hash_manifest(run_dir)
    print(f"EVIDENCE_DIR={run_dir}")
    print(json.dumps(metrics, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

