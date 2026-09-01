"""Fast sequential expansion of the isolated RW-10 AI-provisional queue.

This intentionally does not touch the Human/Gate queue.  It mirrors the
3,000-frame source quotas while reading each video sequentially, which avoids
the expensive random seeks used by the legacy expansion helper.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "evaluation/rw10_lane_ai_provisional_queue_20260827.json"
DEFAULT_FRAMES_DIR = ROOT / "artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/review_frames"
DEFAULT_MEDIA_DIR = ROOT / "media"

SOURCES = [
    {
        "filename": "dashcam_vietnam_rain+night.mp4",
        "fallbacks": ["dashcam_vietnam_rainnight.mp4"],
        "condition": "rain_night",
        "split": "test",
        "prefix": "dashcam_vietnam_rainnight",
        "target": 400,
        "priority": 0,
    },
    {
        "filename": "dashcam_vietnam_night.mp4",
        "fallbacks": [],
        "condition": "night",
        "split": "val",
        "prefix": "dashcam_vietnam_night",
        "target": 500,
        "priority": 1,
    },
    {
        "filename": "dashcam_vietnam_traffic_multi.mp4",
        "fallbacks": [],
        "condition": "dense_traffic",
        "split": "train",
        "prefix": "dashcam_vietnam_traffic_multi",
        "target": 1000,
        "priority": 2,
    },
    {
        "filename": "dashcam_vietnam.mp4",
        "fallbacks": [],
        "condition": "day",
        "split": "train",
        "prefix": "dashcam_vietnam",
        "target": 1100,
        "priority": 3,
    },
]


def find_video(media_dir: Path, cfg: dict[str, Any]) -> Path:
    for name in [cfg["filename"], *cfg["fallbacks"]]:
        candidate = media_dir / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(cfg["filename"])


def blank_record(
    rec_id: str,
    source: str,
    split: str,
    condition: str,
    priority: int,
    frame_index: int,
    timestamp_s: float,
    image_name: str,
) -> dict[str, Any]:
    return {
        "id": rec_id,
        "source": source,
        "source_sha256": None,
        "split": split,
        "timestamp_s": timestamp_s,
        "frame_index": frame_index,
        "conditions": [condition],
        "image": f"artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/review_frames/{image_name}",
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


def expand(queue_path: Path, frames_dir: Path, media_dir: Path) -> dict[str, Any]:
    queue_data = json.loads(queue_path.read_text(encoding="utf-8"))
    existing = queue_data.get("records", [])
    existing_ids = {r["id"] for r in existing}
    existing_by_condition: dict[str, list[dict[str, Any]]] = {}
    for record in existing:
        conditions = record.get("conditions") or []
        if conditions:
            existing_by_condition.setdefault(conditions[0], []).append(record)

    frames_dir.mkdir(parents=True, exist_ok=True)
    additions: list[dict[str, Any]] = []
    source_report: dict[str, int] = {}

    for cfg in SOURCES:
        video_path = find_video(media_dir, cfg)
        cap = cv2.VideoCapture(str(video_path))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        condition = cfg["condition"]
        current = len(existing_by_condition.get(condition, []))
        needed = max(0, cfg["target"] - current)
        if needed == 0:
            cap.release()
            source_report[video_path.name] = 0
            continue

        used = {
            int(r["frame_index"])
            for r in existing_by_condition.get(condition, [])
            if r.get("frame_index") is not None
        }
        available = [i for i in range(10, max(10, total_frames - 10)) if i not in used]
        sample = available if len(available) <= needed else [available[int(i * len(available) / needed)] for i in range(needed)]
        # The interrupted legacy extractor may already have written some
        # images without persisting records. Reuse those files verbatim.
        planned: list[tuple[int, str, str]] = []
        missing_indices: set[int] = set()
        for frame_index in sample:
            rec_id = f"{cfg['prefix']}-{frame_index:04d}"
            if rec_id in existing_ids:
                rec_id = f"{cfg['prefix']}-add{frame_index:04d}"
            image_name = f"{rec_id}.jpg"
            planned.append((frame_index, rec_id, image_name))
            if not (frames_dir / image_name).exists():
                missing_indices.add(frame_index)

        max_target = max(missing_indices) if missing_indices else -1
        added = 0
        frame_index = 0
        while frame_index <= max_target:
            # grab() skips BGR materialization for non-target frames; retrieve
            # only when a sampled frame is actually needed.
            ok = cap.grab()
            if not ok:
                break
            if frame_index in missing_indices:
                ok, frame = cap.retrieve()
                if not ok or frame is None:
                    frame_index += 1
                    continue
                if frame.shape[1] != 1920 or frame.shape[0] != 1080:
                    frame = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_LANCZOS4)
                rec_id = next(item[1] for item in planned if item[0] == frame_index)
                image_name = next(item[2] for item in planned if item[0] == frame_index)
                if not cv2.imwrite(str(frames_dir / image_name), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95]):
                    raise RuntimeError(f"Failed to write {image_name}")
            frame_index += 1
        cap.release()
        for frame_index, rec_id, image_name in planned:
            if not (frames_dir / image_name).exists():
                continue
            additions.append(blank_record(rec_id, video_path.name, cfg["split"], condition, cfg["priority"], frame_index, round(frame_index / fps, 3), image_name))
            existing_ids.add(rec_id)
            added += 1
        source_report[video_path.name] = added
        print(f"{video_path.name}: current={current}, target={cfg['target']}, added={added}", flush=True)

    all_records = existing + additions
    all_records.sort(key=lambda r: (r.get("review_priority", 9), r.get("source", ""), r.get("timestamp_s", 0)))
    queue_data["records"] = all_records
    queue_data["generated_at"] = datetime.now(timezone.utc).isoformat()
    queue_data["provenance"] = {
        "review_status": "ai_provisional",
        "reviewer": "Codex_AI_Assisted_Reviewer",
        "eligible_as_human_review": False,
        "eligible_as_double_review": False,
    }
    queue_path.write_text(json.dumps(queue_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"previous_total": len(existing), "new_total": len(all_records), "added_count": len(additions), "added_per_source": source_report}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--frames-dir", type=Path, default=DEFAULT_FRAMES_DIR)
    parser.add_argument("--media-dir", type=Path, default=DEFAULT_MEDIA_DIR)
    args = parser.parse_args()
    expand(args.queue, args.frames_dir, args.media_dir)


if __name__ == "__main__":
    main()
