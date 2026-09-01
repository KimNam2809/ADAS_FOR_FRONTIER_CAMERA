"""Parallel Gemini pass for the isolated RW-10 AI-provisional queue.

The legacy reviewer writes ``verified``/Gemini metadata.  This wrapper keeps
the source queue isolated, uses bounded concurrency, and commits only
``ai_provisional`` results with an explicit AI reviewer identity.  Failed API
calls are left as ``ai_error`` for retry rather than treated as labels.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

try:
    from scripts.auto_review_lane_queue import analyze_frame, load_client
except ModuleNotFoundError:  # direct execution from the scripts directory
    from auto_review_lane_queue import analyze_frame, load_client


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "evaluation/rw10_lane_ai_provisional_queue_20260827.json"
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


def review_one(record: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str | None, float]:
    started = time.time()
    try:
        result = analyze_frame(client_for_thread(), image_path(record), record.get("conditions", []), retries=3)
        if result is None:
            return record["id"], None, "missing_or_unreadable_image", time.time() - started
        # analyze_frame's hard-failure fallback is not a model review.
        if str(result.get("review_notes", "")).startswith("Automated inspection:"):
            return record["id"], None, "model_api_failed_fallback_not_accepted", time.time() - started
        return record["id"], result, None, time.time() - started
    except Exception as exc:  # keep one bad item from aborting the batch
        return record["id"], None, f"{type(exc).__name__}: {exc}", time.time() - started


def run(queue_path: Path, workers: int, checkpoint: int, max_frames: int | None = None) -> dict[str, Any]:
    data = json.loads(queue_path.read_text(encoding="utf-8"))
    records = data.get("records", [])
    by_id = {r["id"]: r for r in records}
    todo = [r for r in records if r.get("review_status") not in {"ai_provisional"}]
    if max_frames is not None:
        todo = todo[:max_frames]
    total_before = sum(1 for r in records if r.get("review_status") == "ai_provisional")
    ok_count = total_before
    errors: dict[str, str] = {}
    completed = 0
    print(f"Queue records: {len(records)} | Already provisional: {total_before} | To process: {len(todo)} | workers={workers}", flush=True)

    with ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="rw10-ai") as pool:
        futures = {pool.submit(review_one, record): record["id"] for record in todo}
        for future in as_completed(futures):
            rec_id, result, error, elapsed = future.result()
            record = by_id[rec_id]
            if result is not None:
                record.update(result)
                record["review_status"] = "ai_provisional"
                record["reviewer"] = "Codex_AI_Assisted_Reviewer"
                record["ai_review_eligible_as_human"] = False
                record["ai_review_eligible_as_double_review"] = False
                ok_count += 1
                state = "OK"
            else:
                record["review_status"] = "ai_error"
                record["reviewer"] = "Codex_AI_Assisted_Reviewer"
                record["ai_error"] = error
                errors[rec_id] = str(error)
                state = "ERROR"
            completed += 1
            print(f"[{completed}/{len(todo)}] {rec_id} {state} ({elapsed:.1f}s)", flush=True)
            if completed % max(1, checkpoint) == 0:
                data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                queue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"Checkpoint saved: provisional={ok_count}, errors={len(errors)}", flush=True)

    data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    data["provenance"] = {
        "review_status": "ai_provisional",
        "reviewer": "Codex_AI_Assisted_Reviewer",
        "eligible_as_human_review": False,
        "eligible_as_double_review": False,
        "parallel_workers": workers,
    }
    queue_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = {"total_records": len(records), "ai_provisional": sum(1 for r in records if r.get("review_status") == "ai_provisional"), "ai_errors": len(errors), "errors": errors}
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--checkpoint", type=int, default=25)
    parser.add_argument("--max-frames", type=int, default=None)
    args = parser.parse_args()
    run(args.queue, args.workers, args.checkpoint, args.max_frames)


if __name__ == "__main__":
    main()
