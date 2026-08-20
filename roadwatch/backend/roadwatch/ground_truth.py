from __future__ import annotations

from collections import defaultdict
from typing import Any


def validate_ground_truth(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if int(payload.get("schema_version", 0)) != 1:
        errors.append("schema_version must be 1")
    seen: set[str] = set()
    for video in payload.get("videos", []):
        source = str(video.get("source", ""))
        if not source:
            errors.append("video.source is required")
        for event in video.get("events", []):
            event_id = str(event.get("id", ""))
            if not event_id or event_id in seen:
                errors.append(f"duplicate/missing event id: {event_id!r}")
            seen.add(event_id)
            start = float(event.get("start_seconds", -1))
            onset = float(event.get("hazard_onset_seconds", -1))
            deadline = float(event.get("deadline_seconds", -1))
            end = float(event.get("end_seconds", -1))
            if not (0 <= start <= onset <= deadline <= end):
                errors.append(f"{event_id}: expected start <= onset <= deadline <= end")
            if event.get("review_status") not in {"verified", "provisional"}:
                errors.append(f"{event_id}: invalid review_status")
            if not event.get("acceptable_event_types"):
                errors.append(f"{event_id}: acceptable_event_types is required")
        for window in video.get("coverage", []):
            if float(window.get("start_seconds", -1)) >= float(window.get("end_seconds", -1)):
                errors.append(f"{source}: invalid coverage window")
    return errors


def events_for_source(payload: dict[str, Any], source: str) -> dict[str, Any] | None:
    source_name = source.replace("\\", "/").rsplit("/", 1)[-1]
    return next(
        (item for item in payload.get("videos", []) if item.get("source") == source_name),
        None,
    )


def score_events(
    predictions: list[dict[str, Any]],
    video_truth: dict[str, Any] | None,
    verified_only: bool = True,
) -> dict[str, Any]:
    if not video_truth:
        return {"status": "not_annotated", "reason": "No timestamp ground truth for source"}
    truth = [
        item
        for item in video_truth.get("events", [])
        if not verified_only or item.get("review_status") == "verified"
    ]
    matched_prediction_ids: set[int] = set()
    matches: list[dict[str, Any]] = []
    missed: list[str] = []
    duplicate_count = 0
    for expected in truth:
        compatible: list[tuple[int, dict[str, Any]]] = []
        accepted_types = set(expected["acceptable_event_types"])
        for index, prediction in enumerate(predictions):
            if index in matched_prediction_ids:
                continue
            timestamp = float(prediction.get("source_time", -1))
            expected_speed = expected.get("speed_value")
            predicted_speed = prediction.get("evidence", {}).get("speed_value")
            if (
                prediction.get("event_type") in accepted_types
                and float(expected["start_seconds"]) <= timestamp <= float(expected["end_seconds"])
                and (expected_speed is None or int(predicted_speed or -1) == int(expected_speed))
            ):
                compatible.append((index, prediction))
        if not compatible:
            missed.append(expected["id"])
            continue
        compatible.sort(key=lambda item: float(item[1].get("source_time", 0)))
        selected_index, selected = compatible[0]
        matched_prediction_ids.add(selected_index)
        duplicate_count += len(compatible[1:])
        warning_time = float(selected["source_time"])
        matches.append(
            {
                "ground_truth_id": expected["id"],
                "predicted_event_type": selected["event_type"],
                "warning_time_seconds": warning_time,
                "time_to_warning_seconds": round(
                    warning_time - float(expected["hazard_onset_seconds"]), 3
                ),
                "deadline_met": warning_time <= float(expected["deadline_seconds"]),
            }
        )

    coverage = [
        item
        for item in video_truth.get("coverage", [])
        if item.get("review_status") == "verified" and item.get("exhaustive", False)
    ]
    false_predictions: list[dict[str, Any]] = []
    for index, prediction in enumerate(predictions):
        if index in matched_prediction_ids:
            continue
        timestamp = float(prediction.get("source_time", -1))
        if any(
            float(window["start_seconds"]) <= timestamp <= float(window["end_seconds"])
            for window in coverage
        ):
            false_predictions.append(
                {
                    "event_type": prediction.get("event_type"),
                    "source_time": timestamp,
                    "message": prediction.get("message"),
                }
            )
    for window in video_truth.get("negative_windows", []):
        if window.get("review_status") != "verified":
            continue
        forbidden = set(window.get("forbidden_event_types", []))
        for index, prediction in enumerate(predictions):
            if index in matched_prediction_ids:
                continue
            timestamp = float(prediction.get("source_time", -1))
            marker = (prediction.get("event_type"), timestamp)
            already_counted = any(
                (item.get("event_type"), item.get("source_time")) == marker
                for item in false_predictions
            )
            if (
                not already_counted
                and prediction.get("event_type") in forbidden
                and float(window["start_seconds"]) <= timestamp <= float(window["end_seconds"])
            ):
                false_predictions.append(
                    {
                        "event_type": prediction.get("event_type"),
                        "source_time": timestamp,
                        "message": prediction.get("message"),
                        "reason": "forbidden_event_in_verified_negative_window",
                    }
                )
    true_positive = len(matches)
    false_positive = len(false_predictions)
    false_negative = len(missed)
    deadlines_met = sum(1 for item in matches if item["deadline_met"])
    coverage_seconds = sum(
        float(item["end_seconds"]) - float(item["start_seconds"]) for item in coverage
    )
    by_type: dict[str, dict[str, int]] = defaultdict(
        lambda: {"ground_truth": 0, "matched": 0}
    )
    for item in truth:
        by_type[str(item["event_type"])]["ground_truth"] += 1
    truth_by_id = {item["id"]: item for item in truth}
    for item in matches:
        expected = truth_by_id[item["ground_truth_id"]]
        by_type[str(expected["event_type"])]["matched"] += 1
    return {
        "status": "measured" if coverage else "partially_annotated",
        "verified_ground_truth_events": len(truth),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(true_positive / max(true_positive + false_positive, 1), 4),
        "recall": round(true_positive / max(true_positive + false_negative, 1), 4),
        "miss_rate": round(false_negative / max(len(truth), 1), 4),
        "deadline_success_rate": round(deadlines_met / max(len(truth), 1), 4),
        "false_alerts_per_minute": round(false_positive / max(coverage_seconds / 60.0, 1e-6), 4),
        "duplicate_alert_rate": round(duplicate_count / max(len(predictions), 1), 4),
        "coverage_seconds": round(coverage_seconds, 3),
        "matches": matches,
        "missed_ground_truth_ids": missed,
        "false_predictions": false_predictions,
        "by_type": dict(by_type),
        "qualification": "Only verified events and exhaustive verified coverage are scored.",
    }
