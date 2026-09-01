"""Batch Gemini reviewer for the isolated RW-10 AI-provisional queue.

The single-frame helper is intentionally not used here: free-tier RPM limits
make thousands of independent requests unreliable.  This script sends a
small ordered image batch, validates the returned JSON array, and commits a
record only when its own item is present and structurally valid.  It never
uses ``verified`` or a Human reviewer identity.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from PIL import Image
from google.genai import types

try:
    from scripts.auto_review_lane_queue import load_client, sanitize_and_rescale
except ModuleNotFoundError:
    from auto_review_lane_queue import load_client, sanitize_and_rescale


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "evaluation/rw10_lane_ai_provisional_queue_20260827.json"
AI_REVIEWER = "Codex_AI_Assisted_Reviewer"
MODEL_NAME = os.environ.get("RW10_GEMINI_MODEL", "gemini-2.5-flash")
_local = threading.local()


def client_for_thread() -> Any:
    client = getattr(_local, "client", None)
    if client is None:
        client = load_client()
        _local.client = client
    return client


def image_path(record: dict[str, Any]) -> Path:
    candidate = ROOT / str(record.get("image", ""))
    if candidate.exists():
        return candidate
    return ROOT / "artifacts/kaggle/lane_v2_v3_output/lane_v2_quality_gate/review_frames" / f"{record['id']}.jpg"


def prompt_for(records: list[dict[str, Any]]) -> str:
    lines = [
        "You are an expert autonomous-vehicle lane annotator.",
        "Review each image independently. The image order is exactly the numbered order below.",
        "Return ONLY a valid JSON array with exactly one object per image and the exact id shown.",
        "Do not include markdown, commentary, or omitted items.",
        "For every object use: id, ground_truth_lane_count, ego_left_boundary, ego_right_boundary, marking_type, visibility, road_direction, uncertain, review_notes.",
        "Count visible same-direction lanes. Annotate ego boundaries only when defensible; never guess through vehicles, darkness, rain glare, or occlusion.",
        "Coordinates are integer [x,y] in the original 1920x1080 frame, ordered from far/small y to near/large y.",
        "If no defensible lane is visible: lane_count=0, both boundaries=[], marking_type=[\"unknown\"], uncertain=true.",
        "visibility must be clear, partial, occluded, or not_visible; road_direction must be same_direction, opposing, or unknown.",
    ]
    for idx, record in enumerate(records, 1):
        lines.append(f"Image {idx}: id={record['id']}; conditions={record.get('conditions', [])}")
    return "\n".join(lines)


def review_batch(records: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, str], float]:
    started = time.time()
    errors: dict[str, str] = {}
    try:
        images = []
        for record in records:
            path = image_path(record)
            if not path.exists():
                errors[record["id"]] = "missing_image"
                continue
            with Image.open(path) as original:
                images.append(original.convert("RGB").resize((960, 540), Image.Resampling.BILINEAR))
        if errors:
            return {}, errors, time.time() - started

        response = client_for_thread().models.generate_content(
            model=MODEL_NAME,
            contents=[prompt_for(records), *images],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1),
        )
        parsed = json.loads(response.text.strip())
        if not isinstance(parsed, list) or len(parsed) != len(records):
            raise ValueError(f"expected {len(records)} objects, got {type(parsed).__name__}/{len(parsed) if isinstance(parsed, list) else 'n/a'}")

        by_id: dict[str, dict[str, Any]] = {}
        expected_ids = {r["id"] for r in records}
        for raw in parsed:
            if not isinstance(raw, dict) or raw.get("id") not in expected_ids:
                raise ValueError("response id mismatch")
            rec = next(r for r in records if r["id"] == raw["id"])
            cleaned = sanitize_and_rescale(raw, 1920, 1080, 960, 540, rec.get("conditions", []))
            if cleaned["ground_truth_lane_count"] < 0:
                raise ValueError(f"negative lane count for {rec['id']}")
            cleaned["review_status"] = "ai_provisional"
            cleaned["reviewer"] = AI_REVIEWER
            cleaned["ai_review_eligible_as_human"] = False
            cleaned["ai_review_eligible_as_double_review"] = False
            by_id[rec["id"]] = cleaned
        if set(by_id) != expected_ids:
            raise ValueError("not all requested ids returned")
        return by_id, errors, time.time() - started
    except Exception as exc:
        message = f"{type(exc).__name__}: {exc}"
        return {}, {r["id"]: message for r in records}, time.time() - started


def run(queue_path: Path, batch_size: int, workers: int, checkpoint: int, max_batches: int | None = None) -> dict[str, Any]:
    data = json.loads(queue_path.read_text(encoding="utf-8"))
    records = data.get("records", [])
    by_id = {r["id"]: r for r in records}
    todo = [r for r in records if r.get("review_status") != "ai_provisional"]
    batches = [todo[i : i + batch_size] for i in range(0, len(todo), batch_size)]
    if max_batches is not None:
        batches = batches[:max_batches]
    done = 0
    ok = sum(1 for r in records if r.get("review_status") == "ai_provisional")
    errors: dict[str, str] = {}
    print(f"Queue={len(records)} existing_provisional={ok} batches={len(batches)} batch_size={batch_size} workers={workers}", flush=True)
    with ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="rw10-batch") as pool:
        futures = {pool.submit(review_batch, batch): [r["id"] for r in batch] for batch in batches}
        for future in as_completed(futures):
            result, batch_errors, elapsed = future.result()
            for rec_id, cleaned in result.items():
                by_id[rec_id].update(cleaned)
                ok += 1
            for rec_id, error in batch_errors.items():
                by_id[rec_id]["review_status"] = "ai_error"
                by_id[rec_id]["reviewer"] = AI_REVIEWER
                by_id[rec_id]["ai_error"] = error
                errors[rec_id] = error
            done += 1
            print(f"[{done}/{len(batches)}] ok_batch={len(result)} errors={len(batch_errors)} ({elapsed:.1f}s)", flush=True)
            if done % max(1, checkpoint) == 0:
                data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                queue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"Checkpoint saved: provisional={ok}, errors={len(errors)}", flush=True)
    data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    data["provenance"] = {
        "review_status": "ai_provisional",
        "reviewer": AI_REVIEWER,
        "eligible_as_human_review": False,
        "eligible_as_double_review": False,
        "batch_size": batch_size,
        "parallel_workers": workers,
        "model": MODEL_NAME,
    }
    queue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"total_records": len(records), "ai_provisional": sum(1 for r in records if r.get("review_status") == "ai_provisional"), "ai_errors": sum(1 for r in records if r.get("review_status") == "ai_error"), "errors": errors}
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--batch-size", type=int, default=6)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--checkpoint", type=int, default=10)
    parser.add_argument("--max-batches", type=int, default=None)
    args = parser.parse_args()
    run(args.queue, args.batch_size, args.workers, args.checkpoint, args.max_batches)


if __name__ == "__main__":
    main()
