from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
os.environ["ROADWATCH_DISABLE_AUDIO"] = "1"

from roadwatch.alerts import AlertGovernor  # noqa: E402
from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.perception import PerceptionEngine  # noqa: E402
from roadwatch.risk import RiskEngine  # noqa: E402


def _empty_lane(shape: tuple[int, int]) -> dict[str, Any]:
    return {
        "lane_mask": np.zeros(shape, dtype=np.uint8),
        "drivable_mask": np.zeros(shape, dtype=np.uint8),
        "quality": 0.0,
    }


def trace(
    source: str,
    sample_fps: float,
    start: float,
    duration: float | None,
    sign_model: str | None = None,
    sign_onnx_model: str | None = None,
    speed_classifier_model: str | None = None,
) -> dict[str, Any]:
    config = ConfigManager().snapshot()
    if sign_model:
        config["inference"]["sign_model"] = sign_model
    if sign_onnx_model:
        config["inference"]["sign_onnx_model"] = sign_onnx_model
    if speed_classifier_model:
        config["inference"]["speed_classifier_model"] = speed_classifier_model
    detector = PerceptionEngine(config).signs
    risk = RiskEngine(config)
    governor = AlertGovernor(config)
    path = ConfigManager.media_source(source)
    capture = cv2.VideoCapture(str(path))
    native_fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    if start > 0:
        capture.set(cv2.CAP_PROP_POS_MSEC, start * 1000.0)
    step = max(1, int(round(native_fps / max(sample_fps, 0.1))))
    frame_id = 0
    sampled = 0
    raw_rows: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    latency: list[float] = []
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frame_id += 1
            absolute_frame = int(round(capture.get(cv2.CAP_PROP_POS_FRAMES)))
            source_time = absolute_frame / native_fps
            if duration is not None and source_time > start + duration:
                break
            if frame_id % step:
                continue
            sampled += 1
            signs, elapsed = detector.infer(frame)
            latency.append(elapsed)
            candidates, _, _ = risk.analyze(
                [], signs, _empty_lane(frame.shape[:2]), frame.shape[:2], True,
                frame=frame, timestamp=source_time,
            )
            accepted, _ = governor.decide(
                candidates,
                now=1_700_000_000.0 + source_time,
                clock=source_time,
                frame_id=sampled,
                source_time=source_time,
            )
            events.extend(accepted)
            if signs:
                raw_rows.append(
                    {
                        "source_time": round(source_time, 3),
                        "detections": signs,
                        "trace": risk.last_sign_trace,
                        "events": [
                            {
                                "event_type": item["event_type"],
                                "message": item["message"],
                                "audio_action": item["audio_action"],
                                "audio_status": item["audio_status"],
                                "evidence": item["evidence"],
                            }
                            for item in accepted
                        ],
                    }
                )
    finally:
        capture.release()
    labels = Counter(
        detection["label"]
        for row in raw_rows
        for detection in row["detections"]
    )
    decisions = Counter(
        item["decision"]
        for row in raw_rows
        for item in row["trace"]
    )
    return {
        "source": source,
        "native_fps": native_fps,
        "sample_fps": native_fps / step,
        "sampled_frames": sampled,
        "provider": detector.status(),
        "mean_sign_latency_ms": round(sum(latency) / max(len(latency), 1), 3),
        "raw_detection_counts": dict(labels.most_common()),
        "gate_decision_counts": dict(decisions.most_common()),
        "events": [
            {
                "source_time": item["source_time"],
                "event_type": item["event_type"],
                "severity": item["severity"],
                "message": item["message"],
                "display_message": item["display_message"],
                "spoken_message": item["spoken_message"],
                "audio_action": item["audio_action"],
                "audio_status": item["audio_status"],
                "evidence": item["evidence"],
            }
            for item in events
        ],
        "observations": raw_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace traffic-sign detection through HMI/TTS gates")
    parser.add_argument("sources", nargs="+", help="Video files located in roadwatch/media")
    parser.add_argument("--sample-fps", type=float, default=6.0)
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--sign-model")
    parser.add_argument("--sign-onnx-model")
    parser.add_argument("--speed-classifier-model")
    parser.add_argument("--output", default="reports/traffic-sign-trace.json")
    args = parser.parse_args()
    report = {
        "videos": [
            trace(
                source,
                args.sample_fps,
                args.start,
                args.duration,
                args.sign_model,
                args.sign_onnx_model,
                args.speed_classifier_model,
            )
            for source in args.sources
        ]
    }
    output = PROJECT_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for video in report["videos"]:
        print(json.dumps({key: video[key] for key in (
            "source", "sampled_frames", "mean_sign_latency_ms",
            "raw_detection_counts", "gate_decision_counts", "events",
        )}, ensure_ascii=False, indent=2))
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
