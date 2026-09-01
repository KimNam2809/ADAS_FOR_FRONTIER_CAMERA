from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_twinlitenetplus_onnx_vs_yolop import (  # noqa: E402
    TwinLiteNetPlusOnnxSegmenter,
)
from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.perception import YOLOPSegmenter  # noqa: E402


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * ratio))]


def dilated(mask: np.ndarray, radius: int = 3) -> np.ndarray:
    size = radius * 2 + 1
    return cv2.dilate(mask.astype(np.uint8), np.ones((size, size), np.uint8)) > 0


def boundary_metrics(predicted: np.ndarray, truth: np.ndarray) -> dict[str, float | None]:
    pred = predicted.astype(bool)
    gt = truth.astype(bool)
    if not gt.any():
        return {"precision": None, "recall": None, "f1": None}
    pred_count = int(pred.sum())
    gt_count = int(gt.sum())
    precision = float(np.logical_and(pred, dilated(gt)).sum() / max(pred_count, 1))
    recall = float(np.logical_and(gt, dilated(pred)).sum() / max(gt_count, 1))
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate_model(model: Any, records: list[dict[str, Any]], package_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for record in records:
        frame_path = ROOT / record["frame_path"]
        mask_path = ROOT / record["lane_boundary_mask_path"]
        frame = cv2.imread(str(frame_path), cv2.IMREAD_COLOR)
        truth = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if frame is None or truth is None:
            rows.append({"id": record["id"], "error": "missing_frame_or_mask"})
            continue
        output, latency = model.infer(frame)
        metrics = boundary_metrics(output["lane_mask"], truth)
        rows.append(
            {
                "id": record["id"],
                "source": record["source"],
                "conditions": record.get("conditions", []),
                "ground_truth_lane_count": record.get("ground_truth_lane_count"),
                "ground_truth_boundary_pixels": int(np.count_nonzero(truth)),
                "predicted_lane_pixels": int(np.count_nonzero(output["lane_mask"])),
                "latency_ms": round(float(latency), 3),
                "boundary_precision": metrics["precision"],
                "boundary_recall": metrics["recall"],
                "boundary_f1": metrics["f1"],
            }
        )
    valid = [row for row in rows if row.get("error") is None]
    positive = [row for row in valid if row.get("boundary_f1") is not None]
    f1_values = [float(row["boundary_f1"]) for row in positive]
    precision_values = [float(row["boundary_precision"]) for row in positive]
    recall_values = [float(row["boundary_recall"]) for row in positive]
    latency_values = [float(row["latency_ms"]) for row in valid]
    return {
        "samples": len(valid),
        "positive_boundary_samples": len(positive),
        "missing_artifacts": len(rows) - len(valid),
        "boundary_precision": round(statistics.fmean(precision_values), 4) if precision_values else None,
        "boundary_recall": round(statistics.fmean(recall_values), 4) if recall_values else None,
        "boundary_f1": round(statistics.fmean(f1_values), 4) if f1_values else None,
        "latency_p50_ms": round(percentile(latency_values, 0.50), 3),
        "latency_p95_ms": round(percentile(latency_values, 0.95), 3),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate YOLOP and TwinLiteNet+ against independent lane ground truth.")
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=ROOT / "evaluation" / "twinlitenetplus_ground_truth_v1" / "manifest.json",
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=ROOT / "models" / "twinlitenetplus_medium.onnx",
    )
    parser.add_argument("--runtime", choices=["cpu", "directml"], default="directml")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports" / "twinlitenetplus_ground_truth_evaluation.json",
    )
    args = parser.parse_args()
    manifest = json.loads(args.ground_truth.read_text(encoding="utf-8"))
    records = manifest.get("records", [])
    base = {
        "schema_version": "roadwatch-lane-model-ground-truth-eval-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ground_truth": str(args.ground_truth),
        "ground_truth_status": manifest.get("status"),
        "ground_truth_independent_of_models": manifest.get("ground_truth_independent_of_models"),
        "runtime": args.runtime,
        "models": {},
        "decision": {
            "automatically_promoted": False,
            "reason": "Promotion requires independent ground truth plus lane-count, LDW and target-edge gates.",
        },
    }
    if manifest.get("status") != "ready_for_model_comparison" or not records:
        base["status"] = "blocked_insufficient_ground_truth"
        base["blocked_reason"] = "Need human-verified, non-uncertain records before model comparison."
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(base, ensure_ascii=False, indent=2))
        return 2

    yolop = YOLOPSegmenter(ConfigManager.model_path("yolop_lane_detection_640.onnx"), args.runtime)
    candidate = TwinLiteNetPlusOnnxSegmenter(args.candidate, args.runtime)
    base["status"] = "complete_diagnostic"
    base["models"]["yolop"] = evaluate_model(yolop, records, args.ground_truth.parent)
    base["models"]["twinlitenetplus_medium_onnx"] = evaluate_model(candidate, records, args.ground_truth.parent)
    base["decision"]["candidate_better_on_boundary_f1"] = (
        base["models"]["twinlitenetplus_medium_onnx"]["boundary_f1"] is not None
        and base["models"]["yolop"]["boundary_f1"] is not None
        and base["models"]["twinlitenetplus_medium_onnx"]["boundary_f1"]
        >= base["models"]["yolop"]["boundary_f1"]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": base["status"], "models": base["models"], "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
