from __future__ import annotations

import json
import random
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.regression import sha256_file  # noqa: E402


TAXONOMY = [
    "fcw",
    "vulnerable_road_user",
    "cut_in",
    "cross_traffic",
    "ldw",
    "lead_vehicle_braking",
    "speed_sign",
    "traffic_sign",
    "fallen_rider",
]
EVENT_TYPE_MAPPING = {"lane_departure": "ldw"}


def queue_to_video_truth(queue: dict) -> dict:
    events = []
    coverage = []
    negative_windows = []
    for window in queue["windows"]:
        coverage.append(
            {
                "start_seconds": window["start_seconds"],
                "end_seconds": window["end_seconds"],
                "exhaustive": bool(window["exhaustive"]),
                "review_status": "verified",
            }
        )
        if window["is_negative"]:
            negative_windows.append(
                {
                    "start_seconds": window["start_seconds"],
                    "end_seconds": window["end_seconds"],
                    "forbidden_event_types": TAXONOMY,
                    "review_status": "verified",
                }
            )
        for index, event in enumerate(window.get("events", []), start=1):
            event_type = EVENT_TYPE_MAPPING.get(event["event_type"], event["event_type"])
            events.append(
                {
                    "id": f"{window['window_id']}-event-{index}",
                    "event_type": event_type,
                    "acceptable_event_types": [event_type],
                    "object_class": event["object_class"],
                    "location": event["location"],
                    "start_seconds": event["start_seconds"],
                    "hazard_onset_seconds": event["hazard_onset_seconds"],
                    "deadline_seconds": event["deadline_seconds"],
                    "end_seconds": event["end_seconds"],
                    "review_status": "verified",
                    "notes": event.get("notes", ""),
                }
            )
    return {
        "source": queue["source"],
        "coverage": coverage,
        "events": events,
        "negative_windows": negative_windows,
    }


def build() -> tuple[dict, dict]:
    queue = json.loads(
        (PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.ground_truth.json").read_text(
            encoding="utf-8"
        )
    )
    legacy = json.loads(
        (PROJECT_ROOT / "evaluation" / "event_ground_truth.json").read_text(encoding="utf-8")
    )
    dashcam_truth = queue_to_video_truth(queue)
    regression_truth = {
        "schema_version": 1,
        "annotation_method": "RW-02 locked human ground truth plus legacy verified locked-media clips",
        "videos": [*legacy["videos"], dashcam_truth],
    }

    scenarios = []
    source_hashes: dict[str, str] = {}

    def add(source: str, start: float, end: float, scenario_id: str, suite: str) -> None:
        truth = next(item for item in regression_truth["videos"] if item["source"] == source)
        expected = sorted(
            {
                event["event_type"]
                for event in truth.get("events", [])
                if float(event["end_seconds"]) >= start and float(event["start_seconds"]) <= end
                and event["review_status"] == "verified"
            }
        )
        source_path = PROJECT_ROOT / "media" / source
        source_hashes.setdefault(source, sha256_file(source_path))
        scenarios.append(
            {
                "id": scenario_id,
                "suite": suite,
                "source": source,
                "source_sha256": source_hashes[source],
                "start_seconds": start,
                "duration_seconds": round(end - start, 3),
                "expected_event_types": expected,
            }
        )

    add("test_video1.mp4", 8.0, 24.0, "locked-tv1-cutin-braking-1", "locked_media")
    add("test_video1.mp4", 26.0, 38.0, "locked-tv1-cutin-braking-2", "locked_media")
    add("video_test.mp4", 10.0, 22.0, "locked-video-test-night", "locked_media")
    add("video_test.mp4", 34.0, 67.0, "locked-video-test-no-speed", "locked_media")
    add("test_video10.mp4", 3.0, 5.0, "locked-tv10-speed-60", "locked_media")
    add("test_video11.mp4", 32.0, 35.0, "locked-tv11-speed-80", "locked_media")

    positives = [window for window in queue["windows"] if window.get("events")]
    negatives = [window for window in queue["windows"] if window.get("is_negative")]
    random.Random(162).shuffle(negatives)
    for window in [*positives, *negatives[:15]]:
        add(
            queue["source"],
            float(window["start_seconds"]),
            float(window["end_seconds"]),
            f"rw02-{window['window_id']}",
            "dashcam_sample",
        )

    truth_path = PROJECT_ROOT / "evaluation" / "regression_ground_truth.json"
    truth_path.write_text(
        json.dumps(regression_truth, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    locked = [
        "configs/release_manifest.json",
        "configs/default.json",
        "evaluation/regression_ground_truth.json",
        "backend/roadwatch/alerts.py",
        "backend/roadwatch/risk.py",
        "backend/roadwatch/pipeline.py",
        "backend/roadwatch/tracking.py",
        "backend/roadwatch/ground_truth.py",
        "backend/roadwatch/regression.py",
        "backend/roadwatch/calibration.py",
        "backend/roadwatch/kinematics.py",
        "scripts/evaluate.py",
        "scripts/build_regression_manifest.py",
        "scripts/run_regression.py",
        "scripts/rescore_regression.py",
        "scripts/evaluate_rw05.py",
        "scripts/evaluate_rw06.py",
        "scripts/evaluate_metric_ttc.py",
        "scripts/validate_calibration.py",
    ]
    manifest = {
        "schema_version": 1,
        "task_id": "RW-03",
        "release_id": json.loads(
            (PROJECT_ROOT / "configs" / "release_manifest.json").read_text(encoding="utf-8")
        )["release_id"],
        "seed": 162,
        "object_profile": "baseline_coco",
        "max_processed_fps": 6.0,
        "event_taxonomy": TAXONOMY,
        "ground_truth": "evaluation/regression_ground_truth.json",
        "locked_artifacts": [
            {"path": item, "sha256": sha256_file(PROJECT_ROOT / item)} for item in locked
        ],
        "selection_policy": {
            "locked_media": "all six legacy verified clips",
            "dashcam_sample": "all 16 positive windows plus 15 negative windows shuffled with seed 162",
        },
        "scenarios": scenarios,
    }
    return regression_truth, manifest


def main() -> int:
    _, manifest = build()
    output = PROJECT_ROOT / "configs" / "regression_manifest.json"
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "built",
                "scenarios": len(manifest["scenarios"]),
                "locked_media": sum(item["suite"] == "locked_media" for item in manifest["scenarios"]),
                "dashcam_sample": sum(item["suite"] == "dashcam_sample" for item in manifest["scenarios"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
