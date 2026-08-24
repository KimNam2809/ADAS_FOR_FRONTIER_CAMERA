from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def timestamp_label(seconds: float) -> str:
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes):02d}:{secs:05.2f}"


def build_storyboard(
    capture: cv2.VideoCapture,
    start: float,
    end: float,
    samples: int = 20,
) -> tuple[np.ndarray, list[float]]:
    width, height = 320, 180
    canvas = np.full((4 * 210, 5 * width, 3), 242, dtype=np.uint8)
    fps = float(capture.get(cv2.CAP_PROP_FPS)) or 30.0
    frame_total = max(samples, int(round((end - start) * fps)))
    target_offsets = {
        int(round(value)): slot
        for slot, value in enumerate(np.linspace(0, frame_total - 1, samples))
    }
    decoded: list[float] = []
    capture.set(cv2.CAP_PROP_POS_MSEC, start * 1000.0)
    for frame_offset in range(frame_total):
        ok, frame = capture.read()
        if not ok:
            break
        slot = target_offsets.get(frame_offset)
        if slot is None:
            continue
        timestamp = start + frame_offset / fps
        thumb = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
        row, col = divmod(slot, 5)
        x, y = col * width, row * 210
        canvas[y : y + height, x : x + width] = thumb
        cv2.putText(
            canvas,
            timestamp_label(float(timestamp)),
            (x + 5, y + 201),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            (15, 15, 15),
            1,
            cv2.LINE_AA,
        )
        decoded.append(round(float(timestamp), 3))
    return canvas, decoded


def main() -> int:
    parser = argparse.ArgumentParser(description="Create 2 FPS storyboards for RW-02 review")
    parser.add_argument(
        "--queue",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.json",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "media" / "dashcam_vietnam.mp4",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "review" / "rw02_storyboards",
    )
    args = parser.parse_args()
    queue = json.loads(args.queue.read_text(encoding="utf-8"))
    capture = cv2.VideoCapture(str(args.source))
    if not capture.isOpened():
        raise RuntimeError(f"Không mở được video: {args.source}")
    args.output.mkdir(parents=True, exist_ok=True)
    index: list[dict] = []
    for number, window in enumerate(queue["windows"], start=1):
        storyboard, decoded = build_storyboard(
            capture,
            float(window["start_seconds"]),
            float(window["end_seconds"]),
        )
        cv2.putText(
            storyboard,
            window["window_id"],
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.72,
            (0, 0, 210),
            2,
            cv2.LINE_AA,
        )
        filename = f"{window['window_id']}.jpg"
        cv2.imwrite(str(args.output / filename), storyboard, [cv2.IMWRITE_JPEG_QUALITY, 90])
        index.append(
            {
                "window_id": window["window_id"],
                "file": filename,
                "start_seconds": window["start_seconds"],
                "end_seconds": window["end_seconds"],
                "decoded_samples": len(decoded),
                "sample_timestamps": decoded,
            }
        )
        if number % 10 == 0:
            print(f"storyboards: {number}/{len(queue['windows'])}", flush=True)
    capture.release()
    (args.output / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"storyboards": len(index), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
