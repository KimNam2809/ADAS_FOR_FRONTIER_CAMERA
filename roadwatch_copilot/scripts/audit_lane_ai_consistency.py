"""Run an independent YOLOP consistency audit over the RW-10 lane sidecar.

This script is deliberately read-only with respect to the source sidecar and the
Human Quality Gate queue.  It creates a separate audit artefact so the output
cannot be mistaken for a Human double-review or a ground-truth label.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.perception import YOLOPSegmenter  # noqa: E402


LOW_SIGNAL_THRESHOLD = 0.20
USABLE_SIGNAL_THRESHOLD = 0.48
MODEL_NAME = "yolop_lane_detection_640.onnx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sidecar",
        default="evaluation/rw10_lane_ai_provisional_queue_20260827.json",
    )
    parser.add_argument(
        "--output",
        default="evaluation/rw10_lane_ai_consistency_audit_20260827.json",
    )
    parser.add_argument(
        "--report",
        default="reports/RW10_LANE_AI_CONSISTENCY_AUDIT_20260827.md",
    )
    parser.add_argument(
        "--checkpoint",
        default="evaluation/rw10_lane_ai_consistency_audit_20260827.checkpoint.json",
    )
    parser.add_argument("--runtime", default="cpu")
    parser.add_argument("--checkpoint-every", type=int, default=50)
    return parser.parse_args()


def existing_lane_count(record: dict[str, Any]) -> int:
    value = record.get("ground_truth_lane_count")
    if isinstance(value, int):
        return max(0, value)
    proposal = record.get("model_proposal") or {}
    instances = proposal.get("lane_instances") or []
    return len(instances) if isinstance(instances, list) else 0


def boundary_points(record: dict[str, Any]) -> int:
    left = record.get("ego_left_boundary") or []
    right = record.get("ego_right_boundary") or []
    return (len(left) if isinstance(left, list) else 0) + (
        len(right) if isinstance(right, list) else 0
    )


def signal_band(quality: float) -> str:
    if quality < LOW_SIGNAL_THRESHOLD:
        return "low"
    if quality < USABLE_SIGNAL_THRESHOLD:
        return "medium"
    return "high"


def category(lane_count: int, quality: float) -> str:
    if lane_count == 0 and quality < LOW_SIGNAL_THRESHOLD:
        return "agreement_no_lane_low_signal"
    if lane_count == 0 and quality >= USABLE_SIGNAL_THRESHOLD:
        return "suspect_missed_lane_high_signal"
    if lane_count > 0 and quality < LOW_SIGNAL_THRESHOLD:
        return "suspect_existing_lane_low_signal"
    if lane_count > 0 and quality >= USABLE_SIGNAL_THRESHOLD:
        return "agreement_lane_high_signal"
    return "mixed_signal_medium"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_checkpoint(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"records": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def audit_record(record: dict[str, Any], detector: YOLOPSegmenter) -> dict[str, Any]:
    image_ref = str(record.get("image", ""))
    image_path = PROJECT_ROOT / image_ref
    existing_count = existing_lane_count(record)
    existing_points = boundary_points(record)
    result: dict[str, Any] = {
        "id": record.get("id"),
        "source": record.get("source"),
        "conditions": record.get("conditions", []),
        "timestamp_s": record.get("timestamp_s"),
        "image": image_ref,
        "existing_reviewer": record.get("reviewer"),
        "existing_review_status": record.get("review_status"),
        "existing_model": record.get("ai_review_model"),
        "existing_lane_count": existing_count,
        "existing_boundary_points": existing_points,
        "existing_uncertain": bool(record.get("uncertain", True)),
        "audit_model": MODEL_NAME,
        "audit_human_eligible": False,
    }
    if not image_path.exists():
        result.update(
            {
                "error": "missing_image",
                "yolop_quality": 0.0,
                "yolop_lane_pixels": 0,
                "yolop_signal_band": "error",
                "comparison_category": "error_missing_image",
            }
        )
        return result
    frame = cv2.imread(str(image_path))
    if frame is None:
        result.update(
            {
                "error": "image_decode_failed",
                "yolop_quality": 0.0,
                "yolop_lane_pixels": 0,
                "yolop_signal_band": "error",
                "comparison_category": "error_image_decode",
            }
        )
        return result
    output, latency_ms = detector.infer(frame)
    quality = float(output.get("quality", 0.0))
    result.update(
        {
            "error": detector.error,
            "yolop_quality": round(quality, 4),
            "yolop_lane_pixels": int(output.get("lane_pixels", 0)),
            "yolop_signal_band": signal_band(quality),
            "yolop_provider": output.get("provider", detector.provider),
            "yolop_latency_ms": round(float(latency_ms), 3),
            "comparison_category": category(existing_count, quality),
        }
    )
    if result["error"]:
        result["comparison_category"] = "error_inference"
    return result


def render_report(
    path: Path,
    sidecar_path: Path,
    output_path: Path,
    records: list[dict[str, Any]],
    started_at: str,
    finished_at: str,
    detector: YOLOPSegmenter,
) -> None:
    categories = Counter(row.get("comparison_category") for row in records)
    bands = Counter(row.get("yolop_signal_band") for row in records)
    errors = [row for row in records if row.get("error")]
    suspects = [
        row
        for row in records
        if row.get("comparison_category")
        in {"suspect_missed_lane_high_signal", "suspect_existing_lane_low_signal"}
    ]
    suspects.sort(
        key=lambda row: (
            0 if row["comparison_category"] == "suspect_missed_lane_high_signal" else 1,
            -float(row.get("yolop_quality", 0.0)),
        )
    )
    lines = [
        "# RW-10 Lane AI Consistency Audit (2026-08-27)",
        "",
        "> This is an AI cross-model consistency check, not a Human review, not a double-review credit, and not ground-truth validation.",
        "",
        f"- Source sidecar: `{sidecar_path.as_posix()}`",
        f"- Audit artefact: `{output_path.as_posix()}`",
        f"- Records processed: **{len(records)}**",
        f"- Started: `{started_at}`; finished: `{finished_at}`",
        f"- YOLOP model: `{MODEL_NAME}`; provider: `{detector.provider}`",
        f"- Errors: **{len(errors)}**",
        "",
        "## Heuristic bands",
        "",
        f"YOLOP quality is a mask-density signal, not accuracy. `low` < {LOW_SIGNAL_THRESHOLD:.2f}; `medium` >= {LOW_SIGNAL_THRESHOLD:.2f} and < {USABLE_SIGNAL_THRESHOLD:.2f}; `high` >= {USABLE_SIGNAL_THRESHOLD:.2f}. The {USABLE_SIGNAL_THRESHOLD:.2f} boundary is inherited from the lane benchmark's usable-coverage diagnostic and is not a label threshold.",
        "",
        "## Category counts",
        "",
    ]
    for key, value in sorted(categories.items(), key=lambda item: str(item[0])):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## YOLOP signal bands", ""])
    for key, value in sorted(bands.items(), key=lambda item: str(item[0])):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Highest-priority suspect records", ""])
    if suspects:
        lines.append("| ID | Conditions | Existing lanes | YOLOP quality | Category |")
        lines.append("|---|---|---:|---:|---|")
        for row in suspects[:25]:
            conditions = ", ".join(row.get("conditions") or [])
            lines.append(
                f"| `{row.get('id')}` | {conditions} | {row.get('existing_lane_count')} | {float(row.get('yolop_quality', 0.0)):.4f} | `{row.get('comparison_category')}` |"
            )
    else:
        lines.append("No record crossed the configured suspect heuristics.")
    lines.extend(
        [
            "",
            "## Required human action",
            "",
            "Review the suspect rows against the raw video/frame first, then review a sample of agreement rows from each condition. Only a real Human Reviewer may change the queue label to `verified`; this report must not be used to claim Human double-review or to unlock the fine-tune gate by itself.",
            "",
            "## Limitations",
            "",
            "YOLOP and the prior sidecar model are both automated systems and can share blind spots. Agreement is consistency evidence only; disagreement is a prioritization signal. No empirical accuracy percentage is inferred without an independently adjudicated ground-truth sample.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    sidecar_path = PROJECT_ROOT / args.sidecar
    output_path = PROJECT_ROOT / args.output
    report_path = PROJECT_ROOT / args.report
    checkpoint_path = PROJECT_ROOT / args.checkpoint
    sidecar = read_json(sidecar_path)
    source_records = sidecar.get("records") or []
    started_at = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []
    if checkpoint_path.exists():
        try:
            checkpoint = read_json(checkpoint_path)
            records = checkpoint.get("records") or []
        except (OSError, json.JSONDecodeError):
            records = []
    completed_ids = {row.get("id") for row in records}
    detector = YOLOPSegmenter(ConfigManager.model_path(MODEL_NAME), args.runtime)
    started_clock = time.perf_counter()
    total = len(source_records)
    for index, source_record in enumerate(source_records, start=1):
        record_id = source_record.get("id")
        if record_id in completed_ids:
            continue
        result = audit_record(source_record, detector)
        records.append(result)
        completed_ids.add(record_id)
        if len(records) % max(args.checkpoint_every, 1) == 0 or len(records) == total:
            write_checkpoint(checkpoint_path, records)
            elapsed = time.perf_counter() - started_clock
            rate = len(records) / max(elapsed, 0.001)
            print(
                json.dumps(
                    {
                        "processed": len(records),
                        "total": total,
                        "errors": sum(bool(row.get("error")) for row in records),
                        "elapsed_s": round(elapsed, 1),
                        "rate_per_s": round(rate, 3),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    records.sort(key=lambda row: str(row.get("id")))
    finished_at = datetime.now(timezone.utc).isoformat()
    categories = Counter(row.get("comparison_category") for row in records)
    output = {
        "schema_version": "rw10-lane-ai-consistency-audit-v1",
        "task_id": "RW-10.1",
        "generated_at": finished_at,
        "review_kind": "ai_cross_model_consistency_audit",
        "source_sidecar": args.sidecar,
        "reviewer": "Codex_AI_Assisted_Reviewer",
        "human_eligible": False,
        "double_review_eligible": False,
        "audit_model": MODEL_NAME,
        "runtime": args.runtime,
        "model_status": detector.status(),
        "thresholds": {
            "low_signal_quality_lt": LOW_SIGNAL_THRESHOLD,
            "usable_signal_quality_gte": USABLE_SIGNAL_THRESHOLD,
            "interpretation": "heuristic prioritization only; not ground-truth or accuracy thresholds",
        },
        "summary": {
            "source_records": total,
            "processed_records": len(records),
            "error_records": sum(bool(row.get("error")) for row in records),
            "category_counts": dict(sorted(categories.items(), key=lambda item: str(item[0]))),
        },
        "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    render_report(
        report_path,
        sidecar_path,
        output_path,
        records,
        started_at,
        finished_at,
        detector,
    )
    print(
        json.dumps(
            {
                "output": str(output_path),
                "report": str(report_path),
                "processed": len(records),
                "errors": output["summary"]["error_records"],
                "category_counts": output["summary"]["category_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if len(records) == total and not output["summary"]["error_records"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
