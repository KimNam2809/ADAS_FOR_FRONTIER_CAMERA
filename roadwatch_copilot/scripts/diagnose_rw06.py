from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from roadwatch.ground_truth import events_for_source, score_events  # noqa: E402
from roadwatch.regression import truth_for_scenario  # noqa: E402


def summary(values: list[float]) -> dict:
    values = sorted(values)
    return {
        "min": round(values[0], 4),
        "median": round(statistics.median(values), 4),
        "p90": round(values[min(len(values) - 1, int(len(values) * 0.9))], 4),
        "max": round(values[-1], 4),
    } if values else {}


def main() -> int:
    report = json.loads((ROOT / "reports/rw06-regression.json").read_text(encoding="utf-8"))
    truth = json.loads((ROOT / "evaluation/regression_ground_truth.json").read_text(encoding="utf-8"))
    false_events: list[dict] = []
    matches: list[dict] = []
    for result in report["results"]:
        scenario = result["scenario"]
        start = float(scenario.get("start_seconds", 0))
        video_truth = events_for_source(truth, scenario["source"])
        clip_truth = truth_for_scenario(video_truth, start, start + float(scenario["duration_seconds"]))
        metric = score_events(result.get("events", []), clip_truth)
        by_marker = {
            (event.get("event_type"), round(float(event.get("source_time", -1)), 4)): event
            for event in result.get("events", [])
        }
        for item in metric.get("false_predictions", []):
            if item.get("event_type") in {"fcw", "lead_vehicle_braking"}:
                event = by_marker.get((item["event_type"], round(float(item["source_time"]), 4)))
                if event:
                    false_events.append(event)
        for item in metric.get("matches", []):
            if item.get("predicted_event_type") in {"fcw", "lead_vehicle_braking"}:
                event = by_marker.get(
                    (item["predicted_event_type"], round(float(item["warning_time_seconds"]), 4))
                )
                if event:
                    matches.append(event)
    groups = [("MATCH", matches), ("FALSE", false_events)]
    groups.extend(
        (f"FALSE_{event_type}", [event for event in false_events if event["event_type"] == event_type])
        for event_type in ("fcw", "lead_vehicle_braking")
    )
    for name, events in groups:
        print(name, len(events))
        for key in ("risk_score", "proximity_score", "approaching_score", "relative_closing_rate_per_s", "relative_closing_acceleration_per_s2", "box_width_ratio"):
            values = [
                float(event.get(key, event.get("evidence", {}).get(key, 0)) or 0)
                for event in events
            ]
            print(" ", key, summary(values))
        if name == "MATCH":
            for event in events:
                print(" ", event["event_type"], event["source_time"], event["evidence"])
        if name.startswith("FALSE"):
            for width, rate in ((0.18, 0.20), (0.20, 0.30), (0.22, 0.35)):
                surviving = sum(
                    float(event.get("evidence", {}).get("box_width_ratio", 0) or 0) >= width
                    and float(event.get("evidence", {}).get("relative_closing_rate_per_s", 0) or 0) >= rate
                    and bool(event.get("evidence", {}).get("path_conflict"))
                    for event in events
                )
                print(" ", f"survive width>={width}, rate>={rate}:", surviving)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
