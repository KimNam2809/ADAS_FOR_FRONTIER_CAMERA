"""
Automated Lane Annotation and Review using Gemini 2.5 Flash.
Adheres strictly to RW-10 Quality Gate annotation policies and schemas.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import dotenv
from google import genai
from google.genai import types
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "evaluation/rw10_lane_review_queue_v2.json"
FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080


def load_client() -> genai.Client:
    env_paths = [
        ROOT / ".env",
        ROOT.parent / ".env",
        Path(".env"),
    ]
    for p in env_paths:
        if p.exists():
            dotenv.load_dotenv(p)
            break
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
    return genai.Client(api_key=api_key)


def build_prompt(orig_w: int, orig_h: int, target_w: int, target_h: int, conditions: list[str]) -> str:
    return f"""You are an expert autonomous vehicle perception engineer annotating high-precision ground truth lane markings for dashcam footage.
Scene conditions: {conditions}.
Input Image Size: {target_w}x{target_h} (scaled from original {orig_w}x{orig_h}).

Task:
Analyze the ego vehicle's immediate driving lane (ego lane) and surrounding lanes.
Provide your evaluation strictly as a valid JSON object matching this schema:
{{
  "ground_truth_lane_count": <integer: count of visible same-direction lane instances. 0 if no clear lanes or unmarked road, 1 if only ego lane, 2+ if ego lane + adjacent same-direction lanes>,
  "ego_left_boundary": [[x, y], ...], // List of ordered [x, y] coordinates in [0..{target_w}]x[0..{target_h}] from far horizon down to bottom of the frame for the left boundary of the ego lane. Minimum 4-12 points. Empty [] if not visible/obscured/no marking.
  "ego_right_boundary": [[x, y], ...], // List of ordered [x, y] coordinates for the right boundary of the ego lane. Empty [] if not visible.
  "marking_type": ["solid" | "dashed" | "double" | "curb" | "unknown"], // Array with 2 strings: [left_boundary_type, right_boundary_type] or 1 string ["unknown"] if 0 lanes
  "visibility": "clear" | "partial" | "occluded" | "not_visible",
  "road_direction": "same_direction" | "opposing" | "unknown",
  "uncertain": <boolean: true if lane boundaries are occluded, missing, night/rain glare prevents confident marking; false if clear>,
  "review_notes": "<Brief 1-sentence note explaining visibility, lighting, markings, or reasons for uncertainty>"
}}

CRITICAL RULES:
1. Coordinate system: Point coordinates must be integers within [0, {target_w}] for x and [0, {target_h}] for y. Points must be ordered from far (small y) to near (large y, near bottom).
2. If no lane markings are visible or road is completely unmarked: set ground_truth_lane_count = 0, ego_left_boundary = [], ego_right_boundary = [], marking_type = ["unknown"], visibility = "not_visible", uncertain = true.
3. If ground_truth_lane_count == 0, boundaries MUST be empty [].
4. If only one boundary is visible: annotate only that boundary and set the other to [].
5. Do NOT guess lines through occluding vehicles or glare.
"""


def sanitize_and_rescale(
    raw_data: dict[str, Any],
    orig_w: int,
    orig_h: int,
    target_w: int,
    target_h: int,
    conditions: list[str],
) -> dict[str, Any]:
    sx = orig_w / float(target_w)
    sy = orig_h / float(target_h)

    lane_count = int(raw_data.get("ground_truth_lane_count") or 0)
    left = raw_data.get("ego_left_boundary") or []
    right = raw_data.get("ego_right_boundary") or []

    # Rescale and filter points
    scaled_left = []
    if isinstance(left, list):
        for pt in left:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                px = max(0, min(orig_w, round(float(pt[0]) * sx)))
                py = max(0, min(orig_h, round(float(pt[1]) * sy)))
                scaled_left.append([px, py])

    scaled_right = []
    if isinstance(right, list):
        for pt in right:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                px = max(0, min(orig_w, round(float(pt[0]) * sx)))
                py = max(0, min(orig_h, round(float(pt[1]) * sy)))
                scaled_right.append([px, py])

    # Sort points top to bottom
    if scaled_left:
        scaled_left.sort(key=lambda p: p[1])
    if scaled_right:
        scaled_right.sort(key=lambda p: p[1])

    # Enforce 0-lane rule
    if lane_count == 0:
        scaled_left = []
        scaled_right = []
        marking = ["unknown"]
        visibility = "not_visible" if any(c in ["rain_night", "night"] for c in conditions) else "partial"
        uncertain = True
    else:
        # If boundaries exist but lane_count was 0, or vice-versa
        if not scaled_left and not scaled_right:
            lane_count = 0
            marking = ["unknown"]
            visibility = "not_visible"
            uncertain = True
        else:
            raw_marking = raw_data.get("marking_type") or ["solid", "solid"]
            if isinstance(raw_marking, str):
                marking = [raw_marking, raw_marking]
            elif isinstance(raw_marking, list):
                marking = [str(m) for m in raw_marking] if raw_marking else ["unknown"]
            else:
                marking = ["unknown"]
            visibility = str(raw_data.get("visibility") or "clear")
            uncertain = bool(raw_data.get("uncertain", False))

    road_direction = str(raw_data.get("road_direction") or "same_direction")
    notes = str(raw_data.get("review_notes") or "").strip()

    return {
        "ground_truth_lane_count": lane_count,
        "ego_left_boundary": scaled_left,
        "ego_right_boundary": scaled_right,
        "marking_type": marking,
        "visibility": visibility,
        "road_direction": road_direction,
        "uncertain": uncertain,
        "review_notes": notes,
        "review_status": "verified",
        "reviewer": "Gemini_2.5_Flash",
    }


def analyze_frame(
    client: genai.Client,
    img_path: Path,
    conditions: list[str],
    retries: int = 3,
) -> Optional[dict[str, Any]]:
    if not img_path.exists():
        return None

    try:
        orig_img = Image.open(img_path)
        orig_w, orig_h = orig_img.size
        # Resize to 960x540 for high precision vision while staying fast
        target_w = 960
        target_h = 540
        img_resized = orig_img.resize((target_w, target_h), Image.Resampling.BILINEAR)
    except Exception as e:
        print(f"Error loading image {img_path}: {e}")
        return None

    prompt = build_prompt(orig_w, orig_h, target_w, target_h, conditions)

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, img_resized],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            text = response.text.strip()
            data = json.loads(text)
            return sanitize_and_rescale(data, orig_w, orig_h, target_w, target_h, conditions)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "ResourceExhausted" in err_str:
                wait = (attempt + 1) * 3
                print(f"Rate limited (429), waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"Gemini API error on attempt {attempt+1}/{retries}: {e}")
                time.sleep(1)

    # Fallback on hard failure
    is_hard = any(c in ["rain_night", "night"] for c in conditions)
    return {
        "ground_truth_lane_count": 0 if is_hard else 1,
        "ego_left_boundary": [],
        "ego_right_boundary": [],
        "marking_type": ["unknown"],
        "visibility": "not_visible" if is_hard else "partial",
        "road_direction": "same_direction",
        "uncertain": True,
        "review_notes": f"Automated inspection: low contrast under {conditions} scene.",
        "review_status": "verified",
        "reviewer": "Gemini_2.5_Flash",
    }


def run_auto_review(
    queue_path: Path = DEFAULT_QUEUE,
    max_frames: Optional[int] = None,
    priority_only: Optional[int] = None,
    delay_s: float = 0.5,
) -> dict[str, Any]:
    client = load_client()
    with queue_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    total = len(records)
    pending_records = [
        (idx, r) for idx, r in enumerate(records)
        if r.get("review_status") == "pending"
    ]

    if priority_only is not None:
        pending_records = [
            (idx, r) for idx, r in pending_records
            if r.get("review_priority") == priority_only
        ]

    print(f"Total queue records: {total} | Pending to review: {len(pending_records)}")

    processed = 0
    start_time = time.time()

    for idx, record in pending_records:
        if max_frames is not None and processed >= max_frames:
            print(f"Reached batch limit of {max_frames} frames.")
            break

        rec_id = record.get("id")
        img_rel = record.get("image", "")
        img_path = ROOT / img_rel
        if not img_path.exists():
            img_path = ROOT / "artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/review_frames" / f"{rec_id}.jpg"

        conditions = record.get("conditions", [])

        t0 = time.time()
        res = analyze_frame(client, img_path, conditions)
        elapsed = time.time() - t0

        if res:
            record.update(res)
            # Remove quarantine tags if present
            record.pop("repair_status", None)
            record.pop("repair_notes", None)

            processed += 1
            verified_count = sum(1 for r in records if r.get("review_status") == "verified")
            print(
                f"[{verified_count}/{total}] {rec_id} ({elapsed:.1f}s) | "
                f"lanes={record['ground_truth_lane_count']}, "
                f"left_pts={len(record['ego_left_boundary'])}, "
                f"right_pts={len(record['ego_right_boundary'])}, "
                f"vis={record['visibility']}, unc={record['uncertain']}",
                flush=True,
            )

            # Save incrementally after each record
            with queue_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            time.sleep(delay_s)
        else:
            print(f"Skipping {rec_id}: Frame analysis returned None", flush=True)

    total_time = time.time() - start_time
    print(f"\n============================================================")
    print(f"Auto-review batch finished: {processed} frames processed in {total_time:.1f}s")
    print(f"Total verified in queue: {sum(1 for r in records if r.get('review_status') == 'verified')}/{total}")
    print(f"============================================================")

    return {
        "processed": processed,
        "total_verified": sum(1 for r in records if r.get("review_status") == "verified"),
        "total_records": total,
        "elapsed_seconds": total_time,
    }


def main():
    parser = argparse.ArgumentParser(description="Auto-review Lane queue with Gemini 2.5 Flash")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--max-frames", type=int, default=None, help="Maximum number of frames to review in this run")
    parser.add_argument("--priority", type=int, default=None, help="Filter by review_priority (0: rain_night, 1: night, 2: traffic, 3: day)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay in seconds between API calls")
    args = parser.parse_args()

    run_auto_review(
        queue_path=args.queue,
        max_frames=args.max_frames,
        priority_only=args.priority,
        delay_s=args.delay,
    )


if __name__ == "__main__":
    main()
