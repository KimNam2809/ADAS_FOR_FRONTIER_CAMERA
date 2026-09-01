from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate RoadWatch camera from chessboard images")
    parser.add_argument("--images", default="calibration/*.jpg")
    parser.add_argument("--columns", type=int, default=9, help="inner chessboard corners")
    parser.add_argument("--rows", type=int, default=6, help="inner chessboard corners")
    parser.add_argument("--square-mm", type=float, default=25.0)
    parser.add_argument("--output", type=Path, default=Path("configs/camera_calibration.json"))
    parser.add_argument("--min-images", type=int, default=12)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_paths = sorted(Path().glob(args.images))
    object_template = np.zeros((args.rows * args.columns, 3), np.float32)
    object_template[:, :2] = np.mgrid[0 : args.columns, 0 : args.rows].T.reshape(-1, 2)
    object_template *= float(args.square_mm) / 1000.0
    object_points: list[np.ndarray] = []
    image_points: list[np.ndarray] = []
    used: list[str] = []
    image_size: tuple[int, int] | None = None
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001)
    for path in image_paths:
        image = cv2.imread(str(path))
        if image is None:
            continue
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        image_size = (gray.shape[1], gray.shape[0])
        found, corners = cv2.findChessboardCorners(gray, (args.columns, args.rows))
        if not found:
            continue
        refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        object_points.append(object_template.copy())
        image_points.append(refined)
        used.append(str(path))
    if len(used) < args.min_images or image_size is None:
        raise RuntimeError(
            f"Need at least {args.min_images} valid chessboard images; found {len(used)}"
        )
    rms, matrix, distortion, _, _ = cv2.calibrateCamera(
        object_points, image_points, image_size, None, None
    )
    report = {
        "schema_version": 1,
        "calibrated": True,
        "camera_id": "front-camera-unassigned",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "image_size": list(image_size),
        "pattern_inner_corners": [args.columns, args.rows],
        "square_mm": args.square_mm,
        "valid_image_count": len(used),
        "rms_reprojection_error": round(float(rms), 6),
        "camera_matrix": matrix.tolist(),
        "distortion_coefficients": distortion.reshape(-1).tolist(),
        "fx": float(matrix[0, 0]),
        "fy": float(matrix[1, 1]),
        "cx": float(matrix[0, 2]),
        "cy": float(matrix[1, 2]),
        "quality_gate": {
            "rms_below_1px": bool(rms < 1.0),
            "metric_ttc_alerting_allowed": False,
            "reason": "Closed-course distance/TTC validation is still mandatory",
        },
        "images": used,
        "source_image_sha256": [
            hashlib.sha256(Path(path).read_bytes()).hexdigest().upper() for path in used
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if rms < 1.0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
