from __future__ import annotations

from typing import Any


def evaluate_lane_annotations(records: list[dict[str, Any]]) -> dict[str, Any]:
    reviewed = [item for item in records if item.get("review_status") == "verified"]
    count_pairs = [
        (int(item["ground_truth_lane_count"]), int(item["predicted_lane_count"]))
        for item in reviewed
        if item.get("ground_truth_lane_count") is not None
        and item.get("predicted_lane_count") is not None
    ]
    boundary_f1 = [
        float(item["ego_boundary_f1"])
        for item in reviewed
        if item.get("ego_boundary_f1") is not None
    ]
    ldw_false = sum(int(item.get("ldw_false_alerts", 0)) for item in reviewed)
    measured_minutes = sum(float(item.get("measured_seconds", 0)) for item in reviewed) / 60.0
    lane_count_accuracy = sum(a == b for a, b in count_pairs) / max(len(count_pairs), 1)
    mean_boundary_f1 = sum(boundary_f1) / max(len(boundary_f1), 1)
    ldw_far = ldw_false / max(measured_minutes, 1e-6)
    conditions = {condition for item in reviewed for condition in item.get("conditions", [])}
    gates = {
        "at_least_300_verified_frames": len(reviewed) >= 300,
        "lane_count_accuracy_at_least_095": bool(count_pairs) and lane_count_accuracy >= 0.95,
        "ego_boundary_f1_at_least_090": bool(boundary_f1) and mean_boundary_f1 >= 0.90,
        "ldw_false_alerts_at_most_1_per_minute": measured_minutes > 0 and ldw_far <= 1.0,
        "night_and_rain_present": {"night", "rain"} <= conditions,
    }
    return {
        "status": "pass" if all(gates.values()) else "pending_or_fail",
        "gates": gates,
        "verified_frames": len(reviewed),
        "lane_count_accuracy": round(lane_count_accuracy, 4),
        "ego_boundary_f1": round(mean_boundary_f1, 4),
        "ldw_false_alerts_per_minute": round(ldw_far, 4),
        "conditions": sorted(conditions),
    }
