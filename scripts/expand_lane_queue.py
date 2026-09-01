"""
Expand RW-10 Lane Review Queue to 3,000 target frames.
Samples frames evenly from source videos across exact split assignments
and extracts high-quality 1920x1080 JPEG frames.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "evaluation/rw10_lane_review_queue_v2.json"
DEFAULT_FRAMES_DIR = ROOT / "artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/review_frames"
DEFAULT_MEDIA_DIR = ROOT / "media"

PRIORITY_MAP = {
    "rain_night": 0,
    "night": 1,
    "dense_traffic": 2,
    "day": 3,
}

# Video to split and target quotas
SOURCES_CONFIG = [
    {
        "video_filename": "dashcam_vietnam_rain+night.mp4",
        "fallback_names": ["dashcam_vietnam_rainnight.mp4"],
        "condition": "rain_night",
        "split": "test",
        "prefix": "dashcam_vietnam_rainnight",
        "target_total": 400,
    },
    {
        "video_filename": "dashcam_vietnam_night.mp4",
        "fallback_names": [],
        "condition": "night",
        "split": "val",
        "prefix": "dashcam_vietnam_night",
        "target_total": 500,
    },
    {
        "video_filename": "dashcam_vietnam_traffic_multi.mp4",
        "fallback_names": [],
        "condition": "dense_traffic",
        "split": "train",
        "prefix": "dashcam_vietnam_traffic_multi",
        "target_total": 1000,
    },
    {
        "video_filename": "dashcam_vietnam.mp4",
        "fallback_names": [],
        "condition": "day",
        "split": "train",
        "prefix": "dashcam_vietnam",
        "target_total": 1100,
    },
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_video_path(media_dir: Path, filename: str, fallbacks: list[str]) -> Path:
    p = media_dir / filename
    if p.exists():
        return p
    for fb in fallbacks:
        p = media_dir / fb
        if p.exists():
            return p
    raise FileNotFoundError(f"Video file {filename} not found in {media_dir}")


def expand_queue(
    queue_path: Path = DEFAULT_QUEUE,
    frames_dir: Path = DEFAULT_FRAMES_DIR,
    media_dir: Path = DEFAULT_MEDIA_DIR,
) -> dict[str, Any]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    with queue_path.open("r", encoding="utf-8") as f:
        queue_data = json.load(f)

    existing_records = queue_data.get("records", [])
    existing_ids = {r["id"] for r in existing_records}
    existing_frame_indices: dict[str, set[int]] = {}
    for r in existing_records:
        source = r.get("source")
        idx = r.get("frame_index")
        if source and idx is not None:
            existing_frame_indices.setdefault(source, set()).add(idx)

    print(f"Loaded existing queue: {len(existing_records)} records.")

    new_records = []
    added_per_source = {}

    for cfg in SOURCES_CONFIG:
        vpath = find_video_path(media_dir, cfg["video_filename"], cfg["fallback_names"])
        actual_source_name = vpath.name
        cap = cv2.VideoCapture(str(vpath))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Count current frames in this category
        current_in_cat = sum(
            1 for r in existing_records
            if cfg["condition"] in r.get("conditions", [])
        )
        needed = max(0, cfg["target_total"] - current_in_cat)
        print(
            f"Source [{actual_source_name}] ({cfg['condition']}): "
            f"current={current_in_cat}, target={cfg['target_total']}, needed={needed}"
        )

        if needed <= 0:
            cap.release()
            continue

        used_indices = existing_frame_indices.get(actual_source_name, set())
        # Generate candidate sampling step
        avail_frames = [
            i for i in range(10, total_frames - 10)
            if i not in used_indices
        ]

        if len(avail_frames) < needed:
            print(f"Warning: only {len(avail_frames)} available frames for {actual_source_name}")
            sample_indices = avail_frames
        else:
            step = len(avail_frames) / float(needed)
            sample_indices = [avail_frames[int(i * step)] for i in range(needed)]

        # Extract frames and build records
        count_added = 0
        for f_idx in sample_indices:
            rec_id = f"{cfg['prefix']}-{f_idx:04d}"
            if rec_id in existing_ids:
                # Ensure unique id
                rec_id = f"{cfg['prefix']}-add{f_idx:04d}"

            img_filename = f"{rec_id}.jpg"
            out_img_path = frames_dir / img_filename

            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            if frame.shape[1] != 1920 or frame.shape[0] != 1080:
                frame = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_LANCZOS4)

            cv2.imwrite(str(out_img_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

            timestamp_s = round(f_idx / fps, 3)
            condition = cfg["condition"]
            priority = PRIORITY_MAP.get(condition, 3)

            rel_image_path = f"artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/review_frames/{img_filename}"

            record = {
                "id": rec_id,
                "source": actual_source_name,
                "source_sha256": None,
                "split": cfg["split"],
                "timestamp_s": timestamp_s,
                "frame_index": f_idx,
                "conditions": [condition],
                "image": rel_image_path,
                "review_priority": priority,
                "priority_reason": "hard_condition_first",
                "model_proposal": {
                    "label_status": "candidate_unverified",
                    "accepted": False,
                    "rejection_reasons": ["expanded_sample"],
                    "lane_instances": [],
                    "geometry": {},
                },
                "review_status": "pending",
                "ground_truth_lane_count": None,
                "ego_left_boundary": [],
                "ego_right_boundary": [],
                "marking_type": [],
                "visibility": None,
                "road_direction": None,
                "uncertain": None,
                "predicted_lane_count": None,
                "ego_boundary_f1": None,
                "ldw_false_alerts": 0,
                "measured_seconds": 0,
                "reviewer": None,
                "review_notes": "",
            }

            new_records.append(record)
            existing_ids.add(rec_id)
            count_added += 1

        cap.release()
        added_per_source[actual_source_name] = count_added
        print(f"Extracted {count_added} frames for {actual_source_name}.")

    all_records = existing_records + new_records
    # Sort records by priority, source, timestamp
    all_records.sort(key=lambda r: (r.get("review_priority", 9), r.get("source", ""), r.get("timestamp_s", 0)))

    queue_data["records"] = all_records
    queue_data["generated_at"] = datetime.now(timezone.utc).isoformat()

    with queue_path.open("w", encoding="utf-8") as f:
        json.dump(queue_data, f, ensure_ascii=False, indent=2)

    print(f"\n============================================================")
    print(f"Queue successfully expanded to {len(all_records)} total records!")
    print(f"Added per source: {added_per_source}")
    print(f"Saved to: {queue_path}")
    print(f"============================================================")

    return {
        "previous_total": len(existing_records),
        "new_total": len(all_records),
        "added_count": len(new_records),
        "added_per_source": added_per_source,
    }


def main():
    parser = argparse.ArgumentParser(description="Expand RW-10 Lane Queue to 3000 frames")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--frames-dir", type=Path, default=DEFAULT_FRAMES_DIR)
    parser.add_argument("--media-dir", type=Path, default=DEFAULT_MEDIA_DIR)
    args = parser.parse_args()

    expand_queue(args.queue, args.frames_dir, args.media_dir)


if __name__ == "__main__":
    main()
