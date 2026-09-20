from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def draw_prediction(frame: np.ndarray, predictions: Iterable[dict[str, Any]]) -> np.ndarray:
    canvas = frame.copy()
    for prediction in predictions:
        x1, y1, x2, y2 = [int(round(v)) for v in prediction["bbox"]]
        label = prediction["canonical_label"]
        speed = prediction.get("speed_value")
        caption = f"{label}:{speed}" if speed is not None else label
        caption += f" {prediction['confidence']:.2f}"
        cv2.rectangle(canvas, (x1, y1), (x2, y2), (30, 220, 255), 2)
        cv2.putText(
            canvas,
            caption,
            (x1, max(20, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (30, 220, 255),
            2,
            cv2.LINE_AA,
        )
    return canvas


def make_contact_sheet(images: list[np.ndarray], output: Path, columns: int = 4) -> None:
    if not images:
        return
    width, height = 480, 270
    tiles = [cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA) for image in images]
    rows = (len(tiles) + columns - 1) // columns
    blank = np.zeros_like(tiles[0])
    tiles.extend([blank] * (rows * columns - len(tiles)))
    sheet = np.vstack([np.hstack(tiles[row * columns : (row + 1) * columns]) for row in range(rows)])
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), sheet)


def write_hash_manifest(run_dir: Path) -> None:
    files = sorted(
        path for path in run_dir.rglob("*") if path.is_file() and path.name != "hashes.sha256"
    )
    lines = [f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}" for path in files]
    (run_dir / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")

