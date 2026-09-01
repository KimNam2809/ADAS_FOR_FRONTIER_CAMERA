from __future__ import annotations

import argparse
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_DISTANCES = {5, 10, 15, 20, 30, 40}
REQUIRED_CONDITIONS = {"day", "night"}


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return math.inf
    index = min(len(ordered) - 1, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def evaluate(samples: list[dict]) -> dict:
    distance_errors = [
        abs(float(item["estimated_distance_m"]) - float(item["ground_truth_distance_m"]))
        / max(float(item["ground_truth_distance_m"]), 1e-6)
        for item in samples
    ]
    ttc_errors = [
        abs(float(item["estimated_ttc_s"]) - float(item["ground_truth_ttc_s"]))
        for item in samples
        if item.get("estimated_ttc_s") is not None and item.get("ground_truth_ttc_s") is not None
    ]
    distances = {round(float(item["ground_truth_distance_m"])) for item in samples}
    conditions = {str(item.get("condition", "")).lower() for item in samples}
    median_distance = statistics.median(distance_errors) if distance_errors else math.inf
    p95_distance = percentile(distance_errors, 0.95)
    median_ttc = statistics.median(ttc_errors) if ttc_errors else math.inf
    gates = {
        "all_required_distances_present": REQUIRED_DISTANCES <= distances,
        "day_and_night_present": REQUIRED_CONDITIONS <= conditions,
        "distance_median_error_at_most_010": median_distance <= 0.10,
        "distance_p95_error_at_most_020": p95_distance <= 0.20,
        "ttc_median_absolute_error_at_most_050s": median_ttc <= 0.50,
    }
    return {
        "status": "pass" if all(gates.values()) else "fail",
        "metric_ttc_alerting_allowed": all(gates.values()),
        "gates": gates,
        "sample_count": len(samples),
        "distance_median_relative_error": round(median_distance, 4),
        "distance_p95_relative_error": round(p95_distance, 4),
        "ttc_median_absolute_error_seconds": round(median_ttc, 4),
        "distances_present_m": sorted(distances),
        "conditions_present": sorted(conditions),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RW-07 measured distance/TTC evidence")
    parser.add_argument("--samples", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("evaluation/rw07_metric_gate.json"))
    args = parser.parse_args()
    payload = json.loads(args.samples.read_text(encoding="utf-8"))
    samples = payload.get("samples", payload) if isinstance(payload, dict) else payload
    report = {
        "schema_version": 1,
        "task_id": "RW-07",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(args.samples),
        **evaluate(samples),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
