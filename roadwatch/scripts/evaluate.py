from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
os.environ["ROADWATCH_DISABLE_AUDIO"] = "1"

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.ground_truth import events_for_source, score_events, validate_ground_truth  # noqa: E402
from roadwatch.pipeline import RoadWatchService  # noqa: E402
from roadwatch.storage import Storage  # noqa: E402


def _speed_consistency(events: list[dict[str, Any]]) -> dict[str, Any]:
    checked = 0
    mismatches: list[dict[str, Any]] = []
    for event in events:
        if event["event_type"] != "speed_sign":
            continue
        speed = event.get("evidence", {}).get("speed_value")
        if speed is None:
            continue
        checked += 1
        if str(speed) not in event["message"]:
            mismatches.append({"event_id": event.get("event_uuid"), "speed": speed})
    return {
        "status": "payload_measured" if checked else "not_observed",
        "checked_events": checked,
        "mismatches": mismatches,
        "consistency_rate": round((checked - len(mismatches)) / max(checked, 1), 4),
    }


def _message_consistency(events: list[dict[str, Any]]) -> dict[str, Any]:
    mismatches = [
        {
            "event_id": event.get("event_uuid") or event.get("event_id"),
            "display_message": event.get("display_message"),
            "spoken_message": event.get("spoken_message"),
        }
        for event in events
        if (event.get("display_message") or event.get("message"))
        != (event.get("spoken_message") or event.get("message"))
    ]
    return {
        "status": "payload_measured" if events else "not_observed",
        "checked_events": len(events),
        "mismatches": mismatches,
        "consistency_rate": round((len(events) - len(mismatches)) / max(len(events), 1), 4),
    }


def _scenario_metrics(scenario: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    expected = set(scenario.get("expected_event_types", []))
    observed = {event["event_type"] for event in events}
    matched = expected & observed
    unexpected = observed - expected
    presence_recall = len(matched) / max(len(expected), 1)
    presence_precision = len(matched) / max(len(observed), 1)
    keys = [(event["event_type"], event.get("object_id")) for event in events]
    repeated = max(0, len(keys) - len(set(keys)))
    duration_minutes = float(scenario["duration_seconds"]) / 60.0
    unexpected_events = [event for event in events if event["event_type"] in unexpected]
    expected_speeds = set(scenario.get("expected_speed_values", []))
    observed_speeds = {
        int(event.get("evidence", {}).get("speed_value"))
        for event in events
        if event["event_type"] == "speed_sign"
        and event.get("evidence", {}).get("speed_value") is not None
    }
    speed_match = expected_speeds & observed_speeds
    expected_semantic_units = (expected - {"speed_sign"}) | {
        f"speed:{value}" for value in expected_speeds
    }
    observed_semantic_units = (observed - {"speed_sign"}) | {
        f"speed:{value}" for value in observed_speeds
    }
    return {
        "scenario_presence_precision": round(presence_precision, 4),
        "scenario_presence_recall": round(presence_recall, 4),
        "scenario_miss_rate": round(1.0 - presence_recall, 4),
        "scenario_semantic_recall": round(
            len(expected_semantic_units & observed_semantic_units)
            / max(len(expected_semantic_units), 1),
            4,
        ),
        "matched_event_types": sorted(matched),
        "missing_event_types": sorted(expected - observed),
        "unexpected_event_types": sorted(unexpected),
        "expected_speed_values": sorted(expected_speeds),
        "observed_speed_values": sorted(observed_speeds),
        "missing_speed_values": sorted(expected_speeds - observed_speeds),
        "unexpected_speed_values": sorted(observed_speeds - expected_speeds),
        "speed_ground_truth_accuracy": (
            round(len(speed_match) / len(expected_speeds), 4) if expected_speeds else None
        ),
        "unexpected_alerts_per_minute_proxy": round(
            len(unexpected_events) / max(duration_minutes, 1e-6), 4
        ),
        "repeated_alert_rate": round(repeated / max(len(events), 1), 4),
        "qualification": "Presence-level proxy; chưa phải event-level ground truth.",
    }


def run_scenario(
    scenario: dict[str, Any],
    max_wall_seconds: float,
    object_profile: str,
    ground_truth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    stamp = int(time.time() * 1000)
    runtime = PROJECT_ROOT / "reports" / f"runtime-eval-{scenario['id']}-{stamp}.json"
    database = PROJECT_ROOT / "reports" / f"events-eval-{scenario['id']}-{stamp}.db"
    config = ConfigManager(runtime_path=runtime)
    config.update(
        {
            "app": {
                "loop_video": False,
                "pace_replay": False,
                "max_processed_fps": 6.0,
            },
            "audio": {"enabled": False},
            "inference": {"object_profile": object_profile},
        },
        persist=False,
    )
    storage = Storage(database)
    service = RoadWatchService(config, storage)
    timed_out = False
    started = time.time()
    try:
        service.start(
            scenario["source"],
            float(scenario.get("start_seconds", 0.0)),
            float(scenario["duration_seconds"]),
        )
        while service.is_running and time.time() - started < max_wall_seconds:
            time.sleep(0.25)
        if service.is_running:
            timed_out = True
            service.stop()
        status = service.status()
        events = storage.list_events(500)
    finally:
        service.close()
        storage.close()
    scenario_eval = _scenario_metrics(scenario, events)
    timestamp_metrics = score_events(
        events,
        events_for_source(ground_truth, str(scenario["source"])) if ground_truth else None,
    )
    first_warning = min(
        (float(event.get("source_time", 0.0)) for event in events),
        default=None,
    )
    return {
        "scenario": scenario,
        "completed": not timed_out,
        "wall_seconds": round(time.time() - started, 2),
        "object_profile": object_profile,
        "first_warning_seconds_from_clip_start": (
            round(first_warning - float(scenario.get("start_seconds", 0.0)), 3)
            if first_warning is not None
            else None
        ),
        "source_time_reached": status.get("source_time", 0.0),
        "events": events,
        "mandatory_metrics": {
            "object_detection_map_precision_recall": {
                "status": "not_measured",
                "reason": "Scenario manifest chưa có bounding-box ground truth.",
            },
            "alert_precision_recall_miss_rate": scenario_eval,
            "timestamp_event_metrics": timestamp_metrics,
            "time_to_warning": {
                "status": timestamp_metrics.get("status", "not_measured"),
                "matches": timestamp_metrics.get("matches", []),
                "deadline_success_rate": timestamp_metrics.get("deadline_success_rate"),
            },
            "false_alerts_per_minute": {
                "status": timestamp_metrics.get("status", "not_measured"),
                "value": timestamp_metrics.get("false_alerts_per_minute"),
                "proxy_value": scenario_eval["unexpected_alerts_per_minute_proxy"],
                "qualification": timestamp_metrics.get("qualification"),
            },
            "repeated_alert_rate": timestamp_metrics.get(
                "duplicate_alert_rate", scenario_eval["repeated_alert_rate"]
            ),
            "tts_hud_consistency": {
                **_message_consistency(events),
                "speed_semantic_consistency": _speed_consistency(events),
                "qualification": "So sánh evidence với message payload; audio bị tắt trong evaluation nên chưa đo âm thanh phát ra.",
            },
            "latency_p50_p95": status["metrics"].get("latencies", {}),
            "frame_drop_ratio": status["metrics"].get("frame_drop_ratio", 0.0),
            "sampling_skip_ratio": status["metrics"].get("sampling_skip_ratio", 0.0),
            "overload_drop_ratio": status["metrics"].get("overload_drop_ratio", 0.0),
            "lane_quality_coverage": status["metrics"].get("lane_quality_coverage", 0.0),
            "audio_stale_event_rate": {
                "status": "not_measured",
                "reason": "Audio bị tắt để tách latency perception; unit test đã xác minh stale-event dropping.",
            },
        },
        "runtime_metrics": status["metrics"],
        "models": status.get("models", {}),
        "degraded_reasons": status.get("degraded_reasons", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="RoadWatch scenario evaluation")
    parser.add_argument("--manifest", default="evaluation/scenarios.json")
    parser.add_argument("--scenario", action="append", help="Scenario id; có thể lặp lại")
    parser.add_argument("--max-wall-seconds", type=float, default=900.0)
    parser.add_argument("--object-profile", default="baseline_coco")
    parser.add_argument("--output", default="reports/evaluation-latest.json")
    parser.add_argument("--ground-truth", default="evaluation/event_ground_truth.json")
    args = parser.parse_args()

    manifest = json.loads((PROJECT_ROOT / args.manifest).read_text(encoding="utf-8"))
    selected = manifest["scenarios"]
    if args.scenario:
        wanted = set(args.scenario)
        selected = [item for item in selected if item["id"] in wanted]
    if not selected:
        raise SystemExit("Không tìm thấy scenario được chọn")
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
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "annotation_note": manifest.get("annotation_note"),
        "object_profile": args.object_profile,
        "results": [
            run_scenario(item, args.max_wall_seconds, args.object_profile, ground_truth)
            for item in selected
        ],
    }
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(item["completed"] for item in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
