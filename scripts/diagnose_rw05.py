from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from roadwatch.ground_truth import events_for_source, score_events  # noqa: E402
from roadwatch.regression import truth_for_scenario  # noqa: E402


MANEUVERS = {"vulnerable_road_user", "cut_in", "cross_traffic"}


def main() -> int:
    report = json.loads((ROOT / "reports/rw05-regression-v3.json").read_text(encoding="utf-8"))
    ground_truth = json.loads(
        (ROOT / "evaluation/regression_ground_truth.json").read_text(encoding="utf-8")
    )
    truth_by_id = {
        event["id"]: event
        for video in ground_truth["videos"]
        for event in video.get("events", [])
    }
    for result in report["results"]:
        scenario = result["scenario"]
        start = float(scenario.get("start_seconds", 0.0))
        end = start + float(scenario["duration_seconds"])
        video_truth = events_for_source(ground_truth, scenario["source"])
        clip_truth = truth_for_scenario(video_truth, start, end)
        score = score_events(result.get("events", []), clip_truth)
        missed = [
            truth_by_id[event_id]
            for event_id in score.get("missed_ground_truth_ids", [])
            if truth_by_id[event_id].get("event_type") in MANEUVERS
        ]
        if not missed:
            continue
        print(f"\n{scenario['id']}")
        for event in missed:
            print(
                "  MISS",
                event["id"],
                event["event_type"],
                event.get("object_class"),
                event.get("location"),
                f"{event['start_seconds']:.1f}-{event['end_seconds']:.1f}",
            )
            nearby = [
                prediction
                for prediction in result.get("events", [])
                if prediction.get("event_type") in MANEUVERS
                and float(event["start_seconds"]) - 1.0
                <= float(prediction.get("source_time", -1))
                <= float(event["end_seconds"]) + 1.0
            ]
            for prediction in nearby[:12]:
                evidence = prediction.get("evidence", {})
                print(
                    "    PRED",
                    round(float(prediction.get("source_time", 0)), 2),
                    prediction.get("event_type"),
                    evidence.get("object_label"),
                    evidence.get("movement_direction"),
                    evidence.get("origin_side"),
                    prediction.get("location"),
                    prediction.get("severity"),
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
