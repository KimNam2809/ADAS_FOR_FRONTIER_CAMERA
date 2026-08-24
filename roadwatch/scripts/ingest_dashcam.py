from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def frame_metrics(frame: np.ndarray, previous_gray: np.ndarray | None) -> tuple[dict, np.ndarray]:
    small = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    contrast = float(gray.std())
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    scene_delta = (
        float(cv2.absdiff(gray, previous_gray).mean()) if previous_gray is not None else 0.0
    )
    exposure = max(0.0, 1.0 - abs(brightness - 115.0) / 115.0)
    quality = (
        0.45 * min(blur / 250.0, 1.0)
        + 0.30 * exposure
        + 0.25 * min(contrast / 55.0, 1.0)
    )
    condition = "night" if brightness < 55 else "low_light" if brightness < 85 else "day"
    return {
        "brightness": round(brightness, 3),
        "contrast": round(contrast, 3),
        "blur_score": round(blur, 3),
        "scene_delta": round(scene_delta, 3),
        "quality_score": round(quality, 5),
        "auto_light_condition": condition,
    }, gray


def select_temporally_stratified(samples: list[dict], count: int) -> list[dict]:
    """Cover the whole video, choosing the best frame near every temporal target."""
    if count <= 0 or not samples:
        return []
    if len(samples) <= count:
        return list(samples)
    selected: list[dict] = []
    used: set[int] = set()
    radius = max(2, math.ceil(len(samples) / count))
    for target in np.linspace(0, len(samples) - 1, count):
        center = int(round(float(target)))
        start = max(0, center - radius)
        end = min(len(samples), center + radius + 1)
        candidates = [item for item in samples[start:end] if item["sample_id"] not in used]
        if not candidates:
            candidates = [item for item in samples if item["sample_id"] not in used]
        chosen = max(candidates, key=lambda item: (item["quality_score"], -abs(item["sample_id"] - center)))
        used.add(chosen["sample_id"])
        selected.append(chosen)
    return sorted(selected, key=lambda item: item["timestamp_s"])


def _timestamp_label(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes):02d}:{secs:05.2f}"


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_contact_sheets(frames: list[tuple[dict, np.ndarray]], output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    page_size = 25
    for page, offset in enumerate(range(0, len(frames), page_size), start=1):
        canvas = np.full((5 * 220, 5 * 320, 3), 245, dtype=np.uint8)
        for slot, (metadata, image) in enumerate(frames[offset : offset + page_size]):
            row, col = divmod(slot, 5)
            thumb = cv2.resize(image, (320, 180), interpolation=cv2.INTER_AREA)
            y, x = row * 220, col * 320
            canvas[y : y + 180, x : x + 320] = thumb
            label = f"#{metadata['selection_id']:03d} {_timestamp_label(metadata['timestamp_s'])} {metadata['auto_light_condition']}"
            cv2.putText(canvas, label, (x + 5, y + 202), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (20, 20, 20), 1, cv2.LINE_AA)
        cv2.imwrite(str(output / f"contact_sheet_{page:03d}.jpg"), canvas, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return math.ceil(len(frames) / page_size)


def ingest(source: Path, output: Path, sample_fps: float, selected_count: int) -> dict:
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"Không mở được video: {source}")
    source_fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if source_fps <= 0 or frame_count <= 0:
        raise RuntimeError("Video không cung cấp FPS/frame count hợp lệ")

    output.mkdir(parents=True, exist_ok=True)
    stride = max(1, int(round(source_fps / sample_fps)))
    samples: list[dict] = []
    encoded: dict[int, bytes] = {}
    previous_gray: np.ndarray | None = None
    frame_id = 0
    sample_id = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_id % stride == 0:
            metrics, previous_gray = frame_metrics(frame, previous_gray)
            row = {
                "sample_id": sample_id,
                "frame_id": frame_id,
                "timestamp_s": round(frame_id / source_fps, 3),
                **metrics,
            }
            samples.append(row)
            ok_jpeg, payload = cv2.imencode(".jpg", cv2.resize(frame, (640, 360)), [cv2.IMWRITE_JPEG_QUALITY, 82])
            if ok_jpeg:
                encoded[sample_id] = payload.tobytes()
            sample_id += 1
        frame_id += 1
    capture.release()

    selected = select_temporally_stratified(samples, selected_count)
    frames_dir = output / "selected_frames"
    frames_dir.mkdir(exist_ok=True)
    contact_frames: list[tuple[dict, np.ndarray]] = []
    selected_rows: list[dict] = []
    for selection_id, row in enumerate(selected, start=1):
        item = dict(row)
        item["selection_id"] = selection_id
        item["needs_human_scene_label"] = True
        item["human_scene_label"] = ""
        filename = f"rw01_{selection_id:04d}_t{int(round(row['timestamp_s'] * 1000)):010d}.jpg"
        item["file"] = f"selected_frames/{filename}"
        payload = encoded.get(row["sample_id"])
        if payload is None:
            continue
        (frames_dir / filename).write_bytes(payload)
        image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
        contact_frames.append((item, image))
        selected_rows.append(item)

    scene_cut_threshold = 35.0
    scene_cuts = [item for item in samples if item["scene_delta"] >= scene_cut_threshold]
    _write_csv(output / "sample_index_2fps.csv", samples)
    _write_csv(output / "selected_frames.csv", selected_rows)
    contact_sheet_count = _write_contact_sheets(contact_frames, output / "contact_sheets")
    light_counts = {
        name: sum(item["auto_light_condition"] == name for item in selected_rows)
        for name in ("day", "low_light", "night")
    }
    inventory = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source.name,
        "source_path_policy": "media-relative; raw video must not be committed",
        "sha256": file_sha256(source),
        "file_size_bytes": source.stat().st_size,
        "width": width,
        "height": height,
        "fps": source_fps,
        "frame_count_reported": frame_count,
        "frame_count_decoded": frame_id,
        "duration_seconds": frame_count / source_fps,
        "sample_fps_requested": sample_fps,
        "sample_stride_frames": stride,
        "indexed_samples": len(samples),
        "selected_frames": len(selected_rows),
        "selected_light_distribution": light_counts,
        "scene_cut_threshold": scene_cut_threshold,
        "scene_cut_candidates": len(scene_cuts),
        "contact_sheets": contact_sheet_count,
        "human_gate": {
            "status": "pending",
            "required_labels": ["day", "night", "rain", "intersection", "dense_traffic", "other"],
            "instruction": "Review contact sheets and fill human_scene_label in selected_frames.csv.",
        },
    }
    (output / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory and stratify a RoadWatch dashcam video")
    parser.add_argument("--source", type=Path, default=PROJECT_ROOT / "media" / "dashcam_vietnam.mp4")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "reports" / "review" / "rw01_dashcam")
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--selected-count", type=int, default=600)
    args = parser.parse_args()
    if not args.source.is_file():
        raise FileNotFoundError(args.source)
    report = ingest(args.source.resolve(), args.output.resolve(), args.sample_fps, args.selected_count)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
