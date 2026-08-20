from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.perception import UFLDv2LaneDetector, YOLOPSegmenter  # noqa: E402


DEFAULT_SAMPLES = {
    "test_video1.mp4": [10, 14, 18, 28, 32, 36],
    "video_test.mp4": [10, 13, 16, 20, 42, 48, 54],
    "test_video10.mp4": [2, 4, 6, 8],
    "test_video11.mp4": [30, 32, 34, 36],
}


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * ratio))]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare YOLOP and UFLDv2 lane geometry")
    parser.add_argument("--output", default="reports/lane-model-comparison.json")
    parser.add_argument("--runtime", default="cpu")
    parser.add_argument("--render-dir", default="reports/review/lane-models")
    args = parser.parse_args()
    models = {
        "yolop": YOLOPSegmenter(
            ConfigManager.model_path("yolop_lane_detection_640.onnx"), args.runtime
        ),
        "ufldv2": UFLDv2LaneDetector(
            ConfigManager.model_path("ufldv2_culane_res18_320x1600.onnx"), args.runtime
        ),
    }
    rows: list[dict] = []
    render_dir = PROJECT_ROOT / args.render_dir
    render_dir.mkdir(parents=True, exist_ok=True)
    for video_name, timestamps in DEFAULT_SAMPLES.items():
        capture = cv2.VideoCapture(str(PROJECT_ROOT / "media" / video_name))
        if not capture.isOpened():
            rows.append({"video": video_name, "error": "cannot_open"})
            continue
        for timestamp in timestamps:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
            ok, frame = capture.read()
            if not ok:
                rows.append({"video": video_name, "timestamp": timestamp, "error": "read_failed"})
                continue
            for model_name, model in models.items():
                output, latency = model.infer(frame)
                if timestamp in timestamps[:2]:
                    overlay = frame.copy()
                    mask = output["lane_mask"].astype(bool)
                    overlay[mask] = (0, 255, 255)
                    rendered = cv2.addWeighted(frame, 0.72, overlay, 0.28, 0)
                    cv2.putText(
                        rendered,
                        f"{model_name} q={float(output.get('quality', 0)):.2f} t={latency:.1f}ms",
                        (24, 48),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1.0,
                        (255, 255, 255),
                        2,
                        cv2.LINE_AA,
                    )
                    cv2.imwrite(
                        str(render_dir / f"{Path(video_name).stem}_{timestamp:05.1f}_{model_name}.jpg"),
                        rendered,
                        [cv2.IMWRITE_JPEG_QUALITY, 88],
                    )
                rows.append(
                    {
                        "video": video_name,
                        "timestamp": timestamp,
                        "model": model_name,
                        "quality": float(output.get("quality", 0)),
                        "lane_count": output.get("lane_count"),
                        "lane_pixels": int(output.get("lane_pixels", 0)),
                        "latency_ms": round(float(latency), 3),
                        "usable": float(output.get("quality", 0)) >= 0.48,
                    }
                )
        capture.release()
    aggregates = {}
    for model_name in models:
        selected = [row for row in rows if row.get("model") == model_name]
        latencies = [float(row["latency_ms"]) for row in selected]
        qualities = [float(row["quality"]) for row in selected]
        aggregates[model_name] = {
            "samples": len(selected),
            "usable_coverage": round(sum(bool(row["usable"]) for row in selected) / max(len(selected), 1), 4),
            "mean_quality": round(statistics.fmean(qualities), 4) if qualities else 0.0,
            "latency_p50_ms": round(percentile(latencies, 0.50), 3),
            "latency_p95_ms": round(percentile(latencies, 0.95), 3),
            "provider": models[model_name].status()["provider"],
        }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "samples": rows,
        "aggregates": aggregates,
        "gate": {
            "default_profile": "yolop",
            "candidate_profile": "ufldv2_fusion",
            "promotion_rule": "manual geometry review + usable coverage not lower + edge latency budget",
            "automatically_promoted": False,
        },
    }
    output_path = PROJECT_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"aggregates": aggregates, "output": str(output_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
