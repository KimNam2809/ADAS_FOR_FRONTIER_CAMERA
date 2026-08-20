from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
os.environ["ROADWATCH_DISABLE_AUDIO"] = "1"

from evaluate import run_scenario  # noqa: E402
from roadwatch.ground_truth import validate_ground_truth  # noqa: E402


def _aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    recalls: list[float] = []
    semantic_recalls: list[float] = []
    unexpected = 0
    total_events = 0
    total_minutes = 0.0
    first_warnings: list[float] = []
    object_p50: list[float] = []
    object_p95: list[float] = []
    completed = 0
    timestamp_tp = 0
    timestamp_fp = 0
    timestamp_fn = 0
    timestamp_coverage_seconds = 0.0
    for result in results:
        if result["completed"]:
            completed += 1
        metrics = result["mandatory_metrics"]
        alert = metrics["alert_precision_recall_miss_rate"]
        expected = result["scenario"].get("expected_event_types", [])
        if expected:
            recalls.append(float(alert["scenario_presence_recall"]))
            semantic_recalls.append(float(alert["scenario_semantic_recall"]))
        unexpected += len(alert["unexpected_event_types"])
        total_events += len(result["events"])
        total_minutes += float(result["scenario"]["duration_seconds"]) / 60.0
        first = result.get("first_warning_seconds_from_clip_start")
        if first is not None:
            first_warnings.append(float(first))
        latency = metrics["latency_p50_p95"].get("object_detection", {})
        if latency:
            object_p50.append(float(latency.get("p50_ms", 0.0)))
            object_p95.append(float(latency.get("p95_ms", 0.0)))
        timestamp = metrics.get("timestamp_event_metrics", {})
        if timestamp.get("status") == "measured":
            timestamp_tp += int(timestamp.get("true_positive", 0))
            timestamp_fp += int(timestamp.get("false_positive", 0))
            timestamp_fn += int(timestamp.get("false_negative", 0))
            timestamp_coverage_seconds += float(timestamp.get("coverage_seconds", 0.0))
    return {
        "completed_scenarios": completed,
        "scenario_count": len(results),
        "mean_presence_recall": round(statistics.fmean(recalls), 4) if recalls else None,
        "mean_semantic_recall": (
            round(statistics.fmean(semantic_recalls), 4) if semantic_recalls else None
        ),
        "alerts_per_minute": round(total_events / max(total_minutes, 1e-6), 4),
        "unexpected_event_types_per_minute_proxy": round(
            unexpected / max(total_minutes, 1e-6), 4
        ),
        "median_first_warning_seconds": (
            round(statistics.median(first_warnings), 3) if first_warnings else None
        ),
        "object_latency_p50_ms_mean": (
            round(statistics.fmean(object_p50), 2) if object_p50 else None
        ),
        "object_latency_p95_ms_mean": (
            round(statistics.fmean(object_p95), 2) if object_p95 else None
        ),
        "timestamp_event_precision": (
            round(timestamp_tp / max(timestamp_tp + timestamp_fp, 1), 4)
            if timestamp_coverage_seconds
            else None
        ),
        "timestamp_event_recall": (
            round(timestamp_tp / max(timestamp_tp + timestamp_fn, 1), 4)
            if timestamp_coverage_seconds
            else None
        ),
        "timestamp_false_alerts_per_minute": (
            round(timestamp_fp / max(timestamp_coverage_seconds / 60.0, 1e-6), 4)
            if timestamp_coverage_seconds
            else None
        ),
        "timestamp_coverage_seconds": round(timestamp_coverage_seconds, 3),
        "qualification": (
            "Recall is scenario-presence level. Unexpected alerts/min is only a proxy until "
            "timestamped event ground truth exists."
        ),
    }


def _promotion_gate(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "all_scenarios_completed": (
            candidate["completed_scenarios"] == candidate["scenario_count"]
        ),
        "presence_recall_not_lower": (
            candidate["mean_presence_recall"] is not None
            and baseline["mean_presence_recall"] is not None
            and candidate["mean_presence_recall"] >= baseline["mean_presence_recall"]
        ),
        "semantic_recall_not_lower": (
            candidate["mean_semantic_recall"] is not None
            and baseline["mean_semantic_recall"] is not None
            and candidate["mean_semantic_recall"] >= baseline["mean_semantic_recall"]
        ),
        "latency_p95_within_25_percent": (
            candidate["object_latency_p95_ms_mean"] is not None
            and baseline["object_latency_p95_ms_mean"] is not None
            and candidate["object_latency_p95_ms_mean"]
            <= baseline["object_latency_p95_ms_mean"] * 1.25
        ),
        "alert_density_within_10_percent": (
            candidate["alerts_per_minute"]
            <= baseline["alerts_per_minute"] * 1.10
        ),
        "timestamp_event_recall_not_lower": (
            candidate.get("timestamp_event_recall") is None
            or baseline.get("timestamp_event_recall") is None
            or candidate["timestamp_event_recall"] >= baseline["timestamp_event_recall"]
        ),
        "timestamp_false_alert_rate_not_higher": (
            candidate.get("timestamp_false_alerts_per_minute") is None
            or baseline.get("timestamp_false_alerts_per_minute") is None
            or candidate["timestamp_false_alerts_per_minute"]
            <= baseline["timestamp_false_alerts_per_minute"]
        ),
    }
    return {
        "automated_checks_passed": all(checks.values()),
        "checks": checks,
        "decision": "manual_review_required" if all(checks.values()) else "keep_baseline",
        "note": (
            "Automated checks cannot authorize promotion. False-alert and time-to-warning "
            "gates require timestamped ground truth/manual review."
        ),
    }


def _unannotated_media_scenarios(annotated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    covered = {str(item["source"]) for item in annotated}
    scenarios: list[dict[str, Any]] = []
    for path in sorted((PROJECT_ROOT / "media").glob("*.mp4")):
        if path.name in covered:
            continue
        capture = cv2.VideoCapture(str(path))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frames = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        capture.release()
        if fps <= 0 or frames <= 0:
            continue
        scenarios.append(
            {
                "id": f"inventory-{path.stem}",
                "source": path.name,
                "start_seconds": 0,
                "duration_seconds": round(frames / fps, 3),
                "conditions": ["unannotated-regression"],
                "expected_event_types": [],
                "expected_speed_values": [],
                "manual_review": (
                    "Stability/latency/alert-density run only; no event ground truth."
                ),
            }
        )
    return scenarios


def main() -> int:
    parser = argparse.ArgumentParser(description="A/B RoadWatch object detector profiles")
    parser.add_argument("--manifest", default="evaluation/scenarios.json")
    parser.add_argument("--scenario", action="append")
    parser.add_argument("--max-wall-seconds", type=float, default=900.0)
    parser.add_argument("--output", default="reports/ab-object-models.json")
    parser.add_argument("--baseline-profile", default="baseline_coco")
    parser.add_argument("--candidate-profile", default="roadwatch_objects_v1")
    parser.add_argument("--include-unannotated-media", action="store_true")
    parser.add_argument("--unannotated-media-only", action="store_true")
    parser.add_argument("--ground-truth", default="evaluation/event_ground_truth.json")
    args = parser.parse_args()
    manifest = json.loads((PROJECT_ROOT / args.manifest).read_text(encoding="utf-8"))
    scenarios = manifest["scenarios"]
    unannotated = _unannotated_media_scenarios(scenarios)
    if args.unannotated_media_only:
        scenarios = unannotated
    elif args.include_unannotated_media:
        scenarios = scenarios + unannotated
    if args.scenario:
        selected = set(args.scenario)
        scenarios = [item for item in scenarios if item["id"] in selected]
    if not scenarios:
        raise SystemExit("Không có scenario để A/B test")
    ground_truth_path = PROJECT_ROOT / args.ground_truth
    ground_truth = (
        json.loads(ground_truth_path.read_text(encoding="utf-8"))
        if ground_truth_path.exists()
        else None
    )
    if ground_truth:
        errors = validate_ground_truth(ground_truth)
        if errors:
            raise SystemExit("Ground truth không hợp lệ: " + "; ".join(errors))

    profiles = [args.baseline_profile, args.candidate_profile]
    runs: dict[str, list[dict[str, Any]]] = {}
    aggregates: dict[str, dict[str, Any]] = {}
    for profile in profiles:
        print(f"A/B profile={profile}: {len(scenarios)} scenarios", flush=True)
        runs[profile] = [
            run_scenario(scenario, args.max_wall_seconds, profile, ground_truth)
            for scenario in scenarios
        ]
        aggregates[profile] = _aggregate(runs[profile])

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "profiles": profiles,
        "aggregates": aggregates,
        "promotion_gate": _promotion_gate(
            aggregates[args.baseline_profile], aggregates[args.candidate_profile]
        ),
        "runs": runs,
    }
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"aggregates": aggregates, "promotion_gate": report["promotion_gate"]}, indent=2))
    return 0 if all(r["completed"] for values in runs.values() for r in values) else 1


if __name__ == "__main__":
    raise SystemExit(main())
