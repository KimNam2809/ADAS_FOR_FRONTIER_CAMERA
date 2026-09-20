from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.cvat_prelabel.cvat_api import CvatClient
from tools.cvat_prelabel.evidence import write_hash_manifest, write_json

ROADWATCH_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare immutable pre-label evidence to reviewed CVAT GT.")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--task-id", type=int, required=True)
    parser.add_argument("--project-id", type=int, required=True)
    parser.add_argument("--env", type=Path, default=ROADWATCH_ROOT / ".env")
    parser.add_argument("--iou", type=float, default=0.5)
    return parser.parse_args()


def iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1) + max(0.0, bx2 - bx1) * max(0.0, by2 - by1) - intersection
    return intersection / union if union > 0 else 0.0


def attr_map(attributes: list[dict[str, Any]], specs: dict[int, str]) -> dict[str, str]:
    return {specs[int(item["spec_id"])]: str(item["value"]) for item in attributes if int(item["spec_id"]) in specs}


def main() -> int:
    args = parse_args()
    client = CvatClient(args.env)
    labels = client.get_labels(project_id=args.project_id)
    label_names = {int(item["id"]): item["name"] for item in labels}
    attr_specs = {
        int(attribute["id"]): attribute["name"]
        for label in labels
        for attribute in label.get("attributes", [])
    }
    pre_payload = json.loads((args.evidence_dir / "cvat_annotation_payload.json").read_text(encoding="utf-8"))
    reviewed = client.get_annotations(args.task_id)

    def normalize(shape: dict[str, Any]) -> dict[str, Any]:
        return {
            "frame": int(shape["frame"]),
            "label": label_names.get(int(shape["label_id"]), f"label:{shape['label_id']}"),
            "bbox": [float(value) for value in shape["points"]],
            "attributes": attr_map(shape.get("attributes", []), attr_specs),
        }

    predictions = [normalize(item) for item in pre_payload.get("shapes", []) if item.get("type") == "rectangle"]
    ground_truth = [normalize(item) for item in reviewed.get("shapes", []) if item.get("type") == "rectangle"]
    pred_by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    gt_by_frame: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in predictions:
        pred_by_frame[item["frame"]].append(item)
    for item in ground_truth:
        gt_by_frame[item["frame"]].append(item)

    exact_tp = 0
    geometry_matches = 0
    class_correct = 0
    speed_correct = 0
    speed_total = 0
    bbox_unchanged = 0
    matched_pred: set[tuple[int, int]] = set()
    matched_gt: set[tuple[int, int]] = set()
    confusion: Counter[str] = Counter()
    match_details: list[dict[str, Any]] = []

    for frame in sorted(set(pred_by_frame) | set(gt_by_frame)):
        candidates: list[tuple[float, int, int]] = []
        for pi, pred in enumerate(pred_by_frame[frame]):
            for gi, gt in enumerate(gt_by_frame[frame]):
                overlap = iou(pred["bbox"], gt["bbox"])
                if overlap >= args.iou:
                    candidates.append((overlap, pi, gi))
        for overlap, pi, gi in sorted(candidates, reverse=True):
            pred_key, gt_key = (frame, pi), (frame, gi)
            if pred_key in matched_pred or gt_key in matched_gt:
                continue
            matched_pred.add(pred_key)
            matched_gt.add(gt_key)
            geometry_matches += 1
            pred, gt = pred_by_frame[frame][pi], gt_by_frame[frame][gi]
            same_class = pred["label"] == gt["label"]
            class_correct += int(same_class)
            exact_tp += int(same_class)
            bbox_unchanged += int(overlap >= 0.9)
            confusion[f"{pred['label']} -> {gt['label']}"] += 1
            pred_speed = pred["attributes"].get("speed_value")
            gt_speed = gt["attributes"].get("speed_value")
            if pred["label"] == "speed_limit_max" and gt["label"] == "speed_limit_max":
                speed_total += 1
                speed_correct += int(pred_speed == gt_speed)
            match_details.append(
                {
                    "frame": frame,
                    "iou": round(overlap, 4),
                    "predicted_label": pred["label"],
                    "reviewed_label": gt["label"],
                    "predicted_speed": pred_speed,
                    "reviewed_speed": gt_speed,
                }
            )

    false_positive = len(predictions) - len(matched_pred)
    false_negative = len(ground_truth) - len(matched_gt)
    precision = exact_tp / len(predictions) if predictions else 0.0
    recall = exact_tp / len(ground_truth) if ground_truth else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    metrics = {
        "comparison_utc": datetime.now(timezone.utc).isoformat(),
        "task_id": args.task_id,
        "prediction_count": len(predictions),
        "reviewed_count": len(ground_truth),
        "geometry_matches": geometry_matches,
        "true_positive_exact_label": exact_tp,
        "false_positive_or_deleted": false_positive,
        "false_negative_or_added": false_negative,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
        "class_accuracy_on_geometry_matches": round(class_correct / geometry_matches, 6) if geometry_matches else None,
        "speed_value_accuracy": round(speed_correct / speed_total, 6) if speed_total else None,
        "speed_matches_evaluated": speed_total,
        "bbox_unchanged_iou_gte_0_9": bbox_unchanged,
        "iou_match_threshold": args.iou,
        "confusion": dict(sorted(confusion.items())),
    }
    output = args.evidence_dir / "review-comparison"
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "reviewed_annotations.json", reviewed)
    write_json(output / "metrics.json", metrics)
    write_json(output / "matches.json", match_details)
    report = f"""# RoadWatch Pre-label vs Human Review

| Metric | Result |
|---|---:|
| Predictions | {len(predictions)} |
| Reviewed annotations | {len(ground_truth)} |
| Precision | {precision:.4f} |
| Recall | {recall:.4f} |
| F1 | {f1:.4f} |
| Class accuracy on matched geometry | {(class_correct / geometry_matches) if geometry_matches else 0:.4f} |
| Speed-value accuracy | {(speed_correct / speed_total) if speed_total else 0:.4f} |
| Deleted/false-positive predictions | {false_positive} |
| Added/missed annotations | {false_negative} |

This report compares the immutable RoadWatch machine snapshot with the current
CVAT annotations. It must only be treated as ground-truth performance after a
human reviewer has completed every frame and marked the review complete.
"""
    (output / "REPORT.md").write_text(report, encoding="utf-8")
    write_hash_manifest(output)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"OUTPUT_DIR={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

