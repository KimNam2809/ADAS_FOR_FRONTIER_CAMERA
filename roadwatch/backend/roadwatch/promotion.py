from __future__ import annotations

import statistics
from typing import Any

from .ground_truth import events_for_source
from .regression import truth_for_scenario


VRU_CLASSES = {"person", "rider", "bicycle", "motorcycle"}


def profile_metrics(report: dict[str, Any], ground_truth: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    coverage_seconds = 0.0
    latency_p95: list[float] = []
    expected_vru_ids: set[str] = set()
    matched_vru_ids: set[str] = set()
    for result in report["results"]:
        scenario = result["scenario"]
        metric = result["mandatory_metrics"]["timestamp_event_metrics"]
        coverage_seconds += float(metric.get("coverage_seconds", 0.0) or 0.0)
        latency = result["mandatory_metrics"].get("latency_p50_p95", {}).get(
            "object_detection", {}
        )
        if latency.get("p95_ms") is not None:
            latency_p95.append(float(latency["p95_ms"]))
        start = float(scenario.get("start_seconds", 0.0))
        end = start + float(scenario["duration_seconds"])
        video_truth = events_for_source(ground_truth, str(scenario["source"]))
        clip_truth = truth_for_scenario(video_truth, start, end) or {}
        clip_vru_ids = {
            str(event["id"])
            for event in clip_truth.get("events", [])
            if str(event.get("object_class")) in VRU_CLASSES
            and event.get("review_status") == "verified"
        }
        expected_vru_ids.update(clip_vru_ids)
        matched_vru_ids.update(
            str(match["ground_truth_id"])
            for match in metric.get("matches", [])
            if str(match["ground_truth_id"]) in clip_vru_ids
        )
    false_positive = int(summary["false_positive"])
    return {
        "event_precision": float(summary["precision"]),
        "event_recall": float(summary["recall"]),
        "false_positive": false_positive,
        "false_alerts_per_minute": round(
            false_positive / max(coverage_seconds / 60.0, 1e-6), 4
        ),
        "coverage_seconds": round(coverage_seconds, 3),
        "object_latency_p95_ms_mean": round(statistics.fmean(latency_p95), 3)
        if latency_p95
        else None,
        "vru_ground_truth_events": len(expected_vru_ids),
        "vru_matched_events": len(matched_vru_ids),
        "vru_recall": round(len(matched_vru_ids) / max(len(expected_vru_ids), 1), 4),
    }


def promotion_gate(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    latency_ok = (
        baseline["object_latency_p95_ms_mean"] is not None
        and candidate["object_latency_p95_ms_mean"] is not None
        and candidate["object_latency_p95_ms_mean"]
        <= baseline["object_latency_p95_ms_mean"] * 1.25
    )
    checks = {
        "event_recall_not_lower": candidate["event_recall"] >= baseline["event_recall"],
        "vru_recall_not_lower": candidate["vru_recall"] >= baseline["vru_recall"],
        "object_latency_p95_within_125_percent": latency_ok,
        "false_alert_rate_not_over_110_percent": candidate["false_alerts_per_minute"]
        <= baseline["false_alerts_per_minute"] * 1.10,
    }
    automated_pass = all(checks.values())
    return {
        "automated_pass": automated_pass,
        "checks": checks,
        "human_review_50_fp_fn": "pending" if automated_pass else "not_required_auto_fail",
        "decision": "human_review_required" if automated_pass else "keep_baseline",
    }
