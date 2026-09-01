from __future__ import annotations

import json
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
VIDEOS = [
    "dashcam_vietnam.mp4",
    "dashcam_vietnam_night.mp4",
    "dashcam_vietnam_rain+night.mp4",
    "dashcam_vietnam_traffic_multi.mp4",
    "test_video1.mp4",
    "test_video5.mp4",
    "video_test.mp4",
]
HARD_SECONDS = 16 + 12 + 16 + 9 + 12 + 10


def main() -> int:
    rows = []
    base_samples = 0
    total_bytes = 0
    for name in VIDEOS:
        path = ROOT / "media" / name
        capture = cv2.VideoCapture(str(path))
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        capture.release()
        duration = frames / max(fps, 1.0)
        base_samples += int(duration) + 1
        total_bytes += path.stat().st_size
        rows.append(
            {
                "name": name,
                "size_mb": round(path.stat().st_size / 1024**2, 2),
                "fps": round(fps, 3),
                "duration_seconds": round(duration, 3),
            }
        )
    estimated_target_frames = base_samples + HARD_SECONDS * 4
    report = {
        "plan_id": "RW-OBJECT-V2",
        "credential_preflight": "blocked_invalid_legacy_kaggle_key",
        "local_video_profile": rows,
        "video_total_gb": round(total_bytes / 1024**3, 3),
        "approved_base_images": {"train": 70796, "val": 10104, "test": 20101},
        "estimated_sampled_target_frames": estimated_target_frames,
        "estimated_working_disk_gb": {"min": 28, "max": 40},
        "estimated_t4x2_gpu_hours": {"min": 5, "max": 8},
        "estimated_quality_gate_eta_hours": {"min": 0.8, "max": 1.8},
        "training_local": False,
        "notes": [
            "Remote Kaggle metadata could not be refreshed because the saved legacy key returns HTTP 401.",
            "Estimates use the previously verified BDD100K+DAWN split and measured local video metadata.",
            "Checkpoint remains a candidate until pseudo-label review and RoadWatch event regression pass.",
        ],
    }
    output = ROOT / "reports" / "object-v2-resource-profile.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
