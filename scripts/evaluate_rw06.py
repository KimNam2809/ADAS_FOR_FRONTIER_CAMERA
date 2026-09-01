from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from roadwatch.ground_truth import events_for_source, score_events  # noqa: E402
from roadwatch.regression import sha256_file, truth_for_scenario  # noqa: E402


EVENT_TYPES = {"fcw", "lead_vehicle_braking"}


def evaluate(report: dict, ground_truth: dict) -> dict:
    expected_ids: set[str] = set()
    matched_ids: set[str] = set()
    emitted: list[dict] = []
    false_events = 0
    false_by_type: Counter[str] = Counter()
    measured_seconds = 0.0
    for result in report["results"]:
        scenario = result["scenario"]
        start = float(scenario.get("start_seconds", 0.0))
        end = start + float(scenario["duration_seconds"])
        video_truth = events_for_source(ground_truth, scenario["source"])
        clip_truth = truth_for_scenario(video_truth, start, end)
        score = score_events(result.get("events", []), clip_truth)
        measured_seconds += float(score.get("coverage_seconds", 0.0))
        for item in score.get("false_predictions", []):
            if item.get("event_type") in EVENT_TYPES:
                false_events += 1
                false_by_type[str(item.get("event_type"))] += 1
        expected_ids.update(
            str(event["id"])
            for event in (clip_truth or {}).get("events", [])
            if event.get("review_status") == "verified"
            and event.get("event_type") in EVENT_TYPES
        )
        matched_ids.update(
            str(match["ground_truth_id"])
            for match in score.get("matches", [])
            if str(match["ground_truth_id"]) in expected_ids
        )
        emitted.extend(
            event for event in result.get("events", []) if event.get("event_type") in EVENT_TYPES
        )

    evidence_labeled = all(
        event.get("evidence", {}).get("kinematics_space") == "image_space"
        and event.get("evidence", {}).get("relative_kinematics_role")
        == "advisory_image_space_only"
        for event in emitted
    )
    no_single_frame = all(
        event.get("evidence", {}).get("single_frame_trigger") is False
        and int(event.get("evidence", {}).get("confirmation_frames_required", 3)) >= 2
        for event in emitted
    )
    braking_confirmed = all(
        int(event.get("evidence", {}).get("confirmation_frames", 0)) >= 3
        for event in emitted
        if event.get("event_type") == "lead_vehicle_braking"
    )
    recall = len(matched_ids) / max(len(expected_ids), 1)
    gates = {
        "relative_event_recall_at_least_090": bool(expected_ids) and recall >= 0.90,
        "no_single_frame_trigger": bool(emitted) and no_single_frame,
        "lead_brake_confirmation_at_least_3_frames": braking_confirmed,
        "all_metrics_labeled_image_space_relative": bool(emitted) and evidence_labeled,
        "false_events_per_minute_at_most_100": (
            false_events / max(measured_seconds / 60.0, 1e-6)
        ) <= 1.0,
    }
    return {
        "status": "pass" if all(gates.values()) else "fail",
        "gates": gates,
        "verified_events": len(expected_ids),
        "matched_events": len(matched_ids),
        "relative_event_recall": round(recall, 4),
        "emitted_events": len(emitted),
        "false_events_in_verified_coverage": false_events,
        "false_events_by_type": dict(false_by_type),
        "false_events_per_minute": round(
            false_events / max(measured_seconds / 60.0, 1e-6), 4
        ),
        "measured_seconds": round(measured_seconds, 3),
        "evidence_scope_warning": (
            "Only two verified FCW/lead-braking events; pass is R0 evidence, "
            "not a production or closed-course safety claim."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RW-06 gates")
    parser.add_argument("--report", default="reports/rw06-regression.json")
    parser.add_argument("--ground-truth", default="evaluation/regression_ground_truth.json")
    parser.add_argument("--output", default="evaluation/rw06_quality_gate.json")
    args = parser.parse_args()
    report_path = ROOT / args.report
    truth_path = ROOT / args.ground_truth
    report = json.loads(report_path.read_text(encoding="utf-8"))
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    payload = {
        "schema_version": 1,
        "task_id": "RW-06",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "report": {"path": args.report, "sha256": sha256_file(report_path)},
            "ground_truth": {"path": args.ground_truth, "sha256": sha256_file(truth_path)},
        },
        **evaluate(report, truth),
    }
    (ROOT / args.output).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
