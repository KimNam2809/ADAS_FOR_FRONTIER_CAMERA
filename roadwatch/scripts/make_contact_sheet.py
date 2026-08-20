from __future__ import annotations

import argparse
import math
from pathlib import Path

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create timestamped video review contact sheet")
    parser.add_argument("source")
    parser.add_argument("--start", type=float, default=0.0)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--step", type=float, default=2.0)
    parser.add_argument("--columns", type=int, default=5)
    parser.add_argument("--width", type=int, default=320)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = (PROJECT_ROOT / "media" / args.source).resolve()
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise SystemExit(f"Cannot open {source}")
    tiles: list[np.ndarray] = []
    time_value = args.start
    try:
        while time_value <= args.start + args.duration + 1e-6:
            capture.set(cv2.CAP_PROP_POS_MSEC, time_value * 1000.0)
            ok, frame = capture.read()
            if not ok:
                break
            height, width = frame.shape[:2]
            tile_height = int(round(height * args.width / max(width, 1)))
            tile = cv2.resize(frame, (args.width, tile_height), interpolation=cv2.INTER_AREA)
            cv2.rectangle(tile, (0, 0), (150, 28), (0, 0, 0), -1)
            cv2.putText(
                tile,
                f"t={time_value:.1f}s",
                (8, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                (255, 255, 255),
                2,
            )
            tiles.append(tile)
            time_value += args.step
    finally:
        capture.release()
    if not tiles:
        raise SystemExit("No frames extracted")
    tile_height = max(tile.shape[0] for tile in tiles)
    rows = math.ceil(len(tiles) / args.columns)
    sheet = np.zeros((rows * tile_height, args.columns * args.width, 3), dtype=np.uint8)
    for index, tile in enumerate(tiles):
        row, column = divmod(index, args.columns)
        sheet[row * tile_height : row * tile_height + tile.shape[0], column * args.width : (column + 1) * args.width] = tile
    output = (PROJECT_ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), sheet):
        raise SystemExit(f"Cannot write {output}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
