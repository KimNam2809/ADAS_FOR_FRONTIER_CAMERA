from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import cv2


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract verified no-sign frames for sign training")
    parser.add_argument("--source", default="video_test.mp4")
    parser.add_argument("--start", type=float, default=34.0)
    parser.add_argument("--end", type=float, default=67.0)
    parser.add_argument("--step", type=float, default=0.5)
    parser.add_argument("--output", default="datasets/roadwatch_sign_hard_negatives")
    args = parser.parse_args()
    source = PROJECT_ROOT / "media" / args.source
    output = PROJECT_ROOT / args.output
    images = output / "images" / "train"
    labels = output / "labels" / "train"
    images.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(source))
    records: list[dict[str, object]] = []
    timestamp = args.start
    try:
        while timestamp <= args.end + 1e-6:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000.0)
            ok, frame = capture.read()
            if not ok:
                break
            stem = f"{Path(args.source).stem}_{timestamp:07.2f}".replace(".", "_")
            image_path = images / f"{stem}.jpg"
            label_path = labels / f"{stem}.txt"
            cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            label_path.touch(exist_ok=True)
            records.append(
                {
                    "source": args.source,
                    "source_time": round(timestamp, 3),
                    "image": image_path.relative_to(output).as_posix(),
                    "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                    "label_policy": "verified_empty_speed_sign_label",
                }
            )
            timestamp += args.step
    finally:
        capture.release()
    manifest = {
        "schema_version": 1,
        "review_status": "verified",
        "scope": "No speed-limit sign in the reviewed video window; empty YOLO labels.",
        "records": records,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "data.yaml").write_text(
        "path: .\ntrain: images/train\nval: images/train\nnames: {}\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "images": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
