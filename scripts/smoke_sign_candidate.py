from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
os.environ["ROADWATCH_DISABLE_AUDIO"] = "1"

from roadwatch.alerts import AlertGovernor  # noqa: E402
from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.perception import PerceptionEngine  # noqa: E402
from roadwatch.risk import RiskEngine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a RoadWatch traffic-sign candidate")
    parser.add_argument("--image", default="OIP.webp", help="Image in roadwatch/media")
    parser.add_argument("--detector", default="roadwatch_detector_v2.pt")
    parser.add_argument("--detector-onnx", default="roadwatch_detector_v2.onnx")
    parser.add_argument("--classifier", default="roadwatch_speed_digits_v2.pt")
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--output", default="reports/sign-candidate-smoke.json")
    args = parser.parse_args()

    image_path = ConfigManager.media_source(args.image)
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise RuntimeError(f"Unreadable smoke-test image: {image_path}")
    config = ConfigManager().snapshot()
    config["inference"].update(
        {
            "sign_model": args.detector,
            "sign_onnx_model": args.detector_onnx,
            "speed_classifier_model": args.classifier,
        }
    )
    sign_engine = PerceptionEngine(config).signs
    risk = RiskEngine(config)
    governor = AlertGovernor(config)
    accepted: list[dict] = []
    detections: list[dict] = []
    latencies: list[float] = []
    final_trace: list[dict] = []
    final_candidates: list[dict] = []
    suppressed: list[dict] = []
    lane = {
        "lane_mask": np.zeros(frame.shape[:2], dtype=np.uint8),
        "drivable_mask": np.zeros(frame.shape[:2], dtype=np.uint8),
        "quality": 0.0,
    }
    for index in range(max(1, args.frames)):
        timestamp = index * 0.2
        detections, latency = sign_engine.infer(frame)
        latencies.append(latency)
        candidates, _, _ = risk.analyze(
            [], detections, lane, frame.shape[:2], True, frame=frame, timestamp=timestamp
        )
        final_candidates = candidates
        final_trace = risk.last_sign_trace
        events, _ = governor.decide(
            candidates,
            now=1_700_000_000.0 + timestamp,
            clock=timestamp,
            frame_id=index + 1,
            source_time=timestamp,
        )
        accepted.extend(events)
        suppressed.extend(governor.last_suppressed)
    report = {
        "image": args.image,
        "provider": sign_engine.status(),
        "frames": max(1, args.frames),
        "mean_latency_ms": round(sum(latencies) / len(latencies), 3),
        "detections": detections,
        "sign_trace": final_trace,
        "final_candidates": final_candidates,
        "suppressed": [
            {
                "event_type": event.get("event_type"),
                "message": event.get("message"),
                "suppression_reason": event.get("suppression_reason"),
            }
            for event in suppressed
        ],
        "events": [
            {
                "event_type": event["event_type"],
                "display_message": event["display_message"],
                "spoken_message": event["spoken_message"],
                "audio_action": event["audio_action"],
                "audio_status": event["audio_status"],
            }
            for event in accepted
        ],
    }
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if any(event["event_type"] == "speed_sign" for event in accepted) else 2


if __name__ == "__main__":
    raise SystemExit(main())
