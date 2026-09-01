from __future__ import annotations

from collections import Counter
from typing import Any


def validate_annotation_queue(payload: dict[str, Any]) -> dict[str, Any]:
    policy = payload.get("policy", {})
    critical_types = set(policy.get("critical_event_types", []))
    allowed_types = set(policy.get("allowed_event_types", []))
    errors: list[str] = []
    event_counts: Counter[str] = Counter()
    verified_seconds = 0.0
    negative_seconds = 0.0
    critical_windows = 0
    independently_reviewed = 0
    disagreements = 0

    previous_end = -1.0
    for window in sorted(payload.get("windows", []), key=lambda item: item.get("start_seconds", -1)):
        window_id = str(window.get("window_id", "missing-window-id"))
        start = float(window.get("start_seconds", -1))
        end = float(window.get("end_seconds", -1))
        if not 0 <= start < end:
            errors.append(f"{window_id}: invalid window bounds")
        if start < previous_end:
            errors.append(f"{window_id}: overlaps previous window")
        previous_end = max(previous_end, end)
        primary_verified = window.get("primary_review", {}).get("status") == "verified"
        if not primary_verified:
            continue
        if not isinstance(window.get("is_negative"), bool):
            errors.append(f"{window_id}: verified review requires boolean is_negative")
            continue
        coverage = end - start if window.get("exhaustive") else 0.0
        verified_seconds += coverage
        if window["is_negative"]:
            if window.get("events"):
                errors.append(f"{window_id}: negative window cannot contain events")
            negative_seconds += coverage

        window_types: set[str] = set()
        for index, event in enumerate(window.get("events", []), start=1):
            event_type = str(event.get("event_type", ""))
            if event_type not in allowed_types:
                errors.append(f"{window_id}/event-{index}: invalid event_type {event_type!r}")
                continue
            event_counts[event_type] += 1
            window_types.add(event_type)
            values = [
                float(event.get("start_seconds", -1)),
                float(event.get("hazard_onset_seconds", -1)),
                float(event.get("deadline_seconds", -1)),
                float(event.get("end_seconds", -1)),
            ]
            if not (start <= values[0] <= values[1] <= values[2] <= values[3] <= end):
                errors.append(f"{window_id}/event-{index}: invalid event timing")

        if window_types & critical_types:
            critical_windows += 1
            secondary = window.get("secondary_review", {})
            if secondary.get("required") is not True or secondary.get("status") != "verified":
                errors.append(f"{window_id}: critical window requires verified secondary review")
            else:
                independently_reviewed += 1
                if secondary.get("agrees_with_primary") is False:
                    disagreements += 1
                    if window.get("adjudication", {}).get("status") != "verified":
                        errors.append(f"{window_id}: disagreement requires adjudication")

    exceptions = payload.get("event_coverage_exceptions", {})
    insufficient_types = [
        event_type
        for event_type in allowed_types
        if event_counts[event_type] < 20 and not str(exceptions.get(event_type) or "").strip()
    ]
    target_coverage = float(policy.get("target_verified_exhaustive_seconds", 600))
    target_negative = float(policy.get("target_verified_negative_seconds", 150))
    max_disagreement = float(policy.get("max_pre_adjudication_disagreement_rate", 0.10))
    disagreement_rate = disagreements / max(independently_reviewed, 1)
    gates = {
        "verified_coverage": verified_seconds >= target_coverage,
        "verified_negative_coverage": negative_seconds >= target_negative,
        "event_type_coverage_or_exception": not insufficient_types,
        "critical_secondary_review": independently_reviewed == critical_windows,
        "pre_adjudication_disagreement": disagreement_rate <= max_disagreement,
        "schema_integrity": not errors,
    }
    return {
        "status": "pass" if all(gates.values()) else "fail",
        "gates": gates,
        "verified_coverage_seconds": round(verified_seconds, 3),
        "verified_negative_seconds": round(negative_seconds, 3),
        "event_counts": dict(event_counts),
        "event_types_below_target_without_exception": sorted(insufficient_types),
        "critical_windows": critical_windows,
        "independently_reviewed_critical_windows": independently_reviewed,
        "pre_adjudication_disagreement_rate": round(disagreement_rate, 4),
        "errors": errors,
    }
