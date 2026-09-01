from __future__ import annotations

from collections import defaultdict
from typing import Any


def _object_family(label: str) -> str:
    return "two_wheeler" if label in {"rider", "bicycle", "motorcycle"} else label


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
    early_tolerance_seconds: float = 0.5,
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
            expected_class = str(expected.get("object_class") or "")
            predicted_class = str(
                prediction.get("evidence", {}).get("object_label") or ""
            )
            object_compatible = (
                not expected_class
                or not predicted_class
                or _object_family(expected_class) == _object_family(predicted_class)
            )
            expected_location = str(expected.get("location") or "")
            predicted_direction = str(
                prediction.get("evidence", {}).get("movement_direction") or ""
            )
            predicted_origin = str(
                prediction.get("evidence", {}).get("origin_side") or ""
            )
            direction_compatible = (
                expected_location not in {"left_to_right", "right_to_left"}
                or not predicted_direction
                or expected_location == predicted_direction
            )
            origin_compatible = (
                expected_location not in {"left", "right"}
                or not predicted_origin
                or expected_location == predicted_origin
            )
            if (
                prediction.get("event_type") in accepted_types
                and float(expected["start_seconds"]) - max(0.0, early_tolerance_seconds)
                <= timestamp
                <= float(expected["end_seconds"])
                and (expected_speed is None or int(predicted_speed or -1) == int(expected_speed))
                and object_compatible
                and direction_compatible
                and origin_compatible
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
                "predicted_location": selected.get("location"),
                "predicted_movement_direction": selected.get("evidence", {}).get(
                    "movement_direction"
                )
                or (
                    "left_to_right"
                    if float(
                        selected.get("evidence", {}).get("relative_lateral_velocity", 0.0)
                        or 0.0
                    )
                    > 0
                    else "right_to_left"
                    if float(
                        selected.get("evidence", {}).get("relative_lateral_velocity", 0.0)
                        or 0.0
                    )
                    < 0
                    else None
                ),
                "predicted_origin_side": selected.get("evidence", {}).get("origin_side"),
                "predicted_object_label": selected.get("evidence", {}).get("object_label"),
            }
        )

    coverage = [
        item
        for item in video_truth.get("coverage", [])
        if item.get("review_status") == "verified" and item.get("exhaustive", False)
    ]
    verified_negative_windows = [
        item
        for item in video_truth.get("negative_windows", [])
        if item.get("review_status") == "verified"
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
                    "severity": prediction.get("severity"),
                }
            )
    for window in verified_negative_windows:
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
                        "severity": prediction.get("severity"),
                        "reason": "forbidden_event_in_verified_negative_window",
                    }
                )
    true_positive = len(matches)
    false_positive = len(false_predictions)
    false_negative = len(missed)
    deadlines_met = sum(1 for item in matches if item["deadline_met"])
    measurement_intervals = sorted(
        (float(item["start_seconds"]), float(item["end_seconds"]))
        for item in [*coverage, *verified_negative_windows]
    )
    merged_intervals: list[list[float]] = []
    for start, end in measurement_intervals:
        if not merged_intervals or start > merged_intervals[-1][1]:
            merged_intervals.append([start, end])
        else:
            merged_intervals[-1][1] = max(merged_intervals[-1][1], end)
    coverage_seconds = sum(end - start for start, end in merged_intervals)
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
        "status": "measured" if measurement_intervals else "partially_annotated",
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
        "matching_early_tolerance_seconds": early_tolerance_seconds,
    }
