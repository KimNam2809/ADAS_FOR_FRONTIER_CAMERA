from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCKED_REGRESSION_MEDIA = {
    "test_video1.mp4",
    "test_video2.mp4",
    "test_video10.mp4",
    "test_video11.mp4",
    "video_test.mp4",
}


def parse_window(value: str) -> tuple[float, float]:
    try:
        start, end = (float(item) for item in value.split(":", 1))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("window must be START:END seconds") from exc
    if start < 0 or end <= start:
        raise argparse.ArgumentTypeError("window end must be greater than start")
    return start, end


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract a video-grouped fallen-rider annotation queue")
    parser.add_argument("source", type=Path)
    parser.add_argument("--window", action="append", type=parse_window, required=True)
    parser.add_argument("--sample-fps", type=float, default=3.0)
    parser.add_argument("--purpose", choices=["training", "evaluation_review"], default="training")
    parser.add_argument("--output", type=Path, default=Path("datasets/fallen_rider_annotation_queue"))
    args = parser.parse_args()
    source = args.source if args.source.is_absolute() else PROJECT_ROOT / "media" / args.source
    source = source.resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    if args.purpose == "training" and source.name in LOCKED_REGRESSION_MEDIA:
        raise RuntimeError(
            f"{source.name} is locked regression media and cannot be extracted as training data"
        )
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open {source}")
    native_fps = float(capture.get(cv2.CAP_PROP_FPS) or 30.0)
    step = max(1, round(native_fps / max(args.sample_fps, 0.1)))
    group_id = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:12]
    output = (PROJECT_ROOT / args.output / f"{source.stem}_{group_id}").resolve()
    images = output / "images"
    images.mkdir(parents=True, exist_ok=True)
    records = []
    try:
        for window_id, (start, end) in enumerate(args.window):
            capture.set(cv2.CAP_PROP_POS_MSEC, start * 1000.0)
            frame_index = 0
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                source_time = float(capture.get(cv2.CAP_PROP_POS_MSEC)) / 1000.0
                if source_time > end:
                    break
                frame_index += 1
                if (frame_index - 1) % step:
                    continue
                name = f"w{window_id:02d}_{source_time:010.3f}.jpg".replace(".", "_")
                target = images / name
                cv2.imwrite(str(target), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                records.append(
                    {
                        "image": str(target.relative_to(output)).replace("\\", "/"),
                        "source_time": round(source_time, 3),
                        "window_id": window_id,
                        "video_group_id": group_id,
                        "annotation_status": "pending",
                        "allowed_labels": [
                            "fallen_person",
                            "fallen_two_wheeler",
                            "hard_negative",
                            "negative",
                        ],
                        "temporal_event": "fallen_rider",
                    }
                )
    finally:
        capture.release()
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "purpose": args.purpose,
        "video_group_id": group_id,
        "split_policy": "all frames from this group must remain in one split",
        "sample_fps": native_fps / step,
        "records": records,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"output": str(output), "frames": len(records), "group": group_id}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
