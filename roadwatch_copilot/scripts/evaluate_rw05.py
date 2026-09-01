from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.ground_truth import events_for_source, score_events  # noqa: E402
from roadwatch.regression import sha256_file, truth_for_scenario  # noqa: E402
from roadwatch.tracking import semantic_family  # noqa: E402


MANEUVER_TYPES = {"vulnerable_road_user", "cut_in", "cross_traffic"}


def evaluate(report: dict, ground_truth: dict) -> dict:
    truth_by_id = {
        str(event["id"]): event
        for video in ground_truth["videos"]
        for event in video.get("events", [])
        if event.get("review_status") == "verified"
    }
    expected_maneuvers: set[str] = set()
    matched_maneuvers: set[str] = set()
    direction_checks = 0
    direction_correct = 0
    direction_mismatches: list[dict] = []
    false_critical = 0
    measured_seconds = 0.0
    duplicate_count = 0
    event_count = 0

    for result in report["results"]:
        scenario = result["scenario"]
        start = float(scenario.get("start_seconds", 0.0))
        end = start + float(scenario["duration_seconds"])
        video_truth = events_for_source(ground_truth, str(scenario["source"]))
        clip_truth = truth_for_scenario(video_truth, start, end)
        metric = score_events(result.get("events", []), clip_truth)
        result["mandatory_metrics"]["timestamp_event_metrics"] = metric
        measured_seconds += float(metric.get("coverage_seconds", 0.0))
        false_critical += sum(
            item.get("severity") == "critical"
            for item in metric.get("false_predictions", [])
        )
        clip_ids = {
            str(event["id"])
            for event in (clip_truth or {}).get("events", [])
            if event.get("review_status") == "verified"
            and event.get("event_type") in MANEUVER_TYPES
        }
        expected_maneuvers.update(clip_ids)
        for match in metric.get("matches", []):
            event_id = str(match["ground_truth_id"])
            if event_id not in clip_ids:
                continue
            matched_maneuvers.add(event_id)
            expected = str(truth_by_id[event_id].get("location", ""))
            predicted_location = str(match.get("predicted_location") or "")
            predicted_direction = str(match.get("predicted_movement_direction") or "")
            predicted_origin = str(match.get("predicted_origin_side") or "")
            if expected in {"left_to_right", "right_to_left"}:
                direction_checks += 1
                correct = predicted_direction == expected
                direction_correct += correct
                if not correct:
                    direction_mismatches.append(
                        {
                            "ground_truth_id": event_id,
                            "expected": expected,
                            "predicted": predicted_direction,
                            "predicted_location": predicted_location,
                        }
                    )
            elif expected in {"left", "right"}:
                direction_checks += 1
                correct = (
                    predicted_origin == expected
                    or (expected == "left" and "trái" in predicted_location)
                    or (expected == "right" and "phải" in predicted_location)
                )
                direction_correct += correct
                if not correct:
                    direction_mismatches.append(
                        {
                            "ground_truth_id": event_id,
                            "expected": expected,
                            "predicted_origin": predicted_origin,
                            "predicted_location": predicted_location,
                        }
                    )

        recent_by_key: dict[tuple[str, str, str], float] = {}
        for event in sorted(result.get("events", []), key=lambda item: item.get("source_time", 0)):
            label = str(event.get("evidence", {}).get("object_label") or "unknown")
            key = (
                str(event.get("event_type")),
                semantic_family(label),
                str(event.get("location")),
            )
            timestamp = float(event.get("source_time", 0.0))
            if key in recent_by_key and timestamp - recent_by_key[key] <= 2.5:
                duplicate_count += 1
            recent_by_key[key] = timestamp
            event_count += 1

    maneuver_recall = len(matched_maneuvers) / max(len(expected_maneuvers), 1)
    direction_accuracy = direction_correct / max(direction_checks, 1)
    duplicate_rate = duplicate_count / max(event_count, 1)
    false_critical_per_minute = false_critical / max(measured_seconds / 60.0, 1e-6)
    gates = {
        "maneuver_recall_at_least_090": maneuver_recall >= 0.90,
        "direction_accuracy_at_least_095": direction_checks > 0 and direction_accuracy >= 0.95,
        "duplicate_event_rate_at_most_005": duplicate_rate <= 0.05,
        "false_critical_per_minute_at_most_010": false_critical_per_minute <= 0.10,
    }
    return {
        "status": "pass" if all(gates.values()) else "fail",
        "gates": gates,
        "maneuver_ground_truth_events": len(expected_maneuvers),
        "maneuver_matched_events": len(matched_maneuvers),
        "maneuver_recall": round(maneuver_recall, 4),
        "direction_checks": direction_checks,
        "direction_correct": direction_correct,
        "direction_accuracy": round(direction_accuracy, 4),
        "direction_mismatches": direction_mismatches,
        "event_count": event_count,
        "duplicate_events": duplicate_count,
        "duplicate_event_rate": round(duplicate_rate, 4),
        "false_critical_events": false_critical,
        "false_critical_per_minute": round(false_critical_per_minute, 4),
        "measured_seconds": round(measured_seconds, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RW-05 DoD gates")
    parser.add_argument("--report", default="reports/rw05-regression-final.json")
    parser.add_argument("--ground-truth", default="evaluation/regression_ground_truth.json")
    parser.add_argument("--output", default="evaluation/rw05_quality_gate.json")
    args = parser.parse_args()
    report_path = PROJECT_ROOT / args.report
    truth_path = PROJECT_ROOT / args.ground_truth
    report = json.loads(report_path.read_text(encoding="utf-8"))
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    metrics = evaluate(report, truth)
    payload = {
        "schema_version": 1,
        "task_id": "RW-05",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "report": {"path": args.report, "sha256": sha256_file(report_path)},
            "ground_truth": {"path": args.ground_truth, "sha256": sha256_file(truth_path)},
        },
        **metrics,
    }
    output = PROJECT_ROOT / args.output
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
