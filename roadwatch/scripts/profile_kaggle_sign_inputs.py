from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASETS = [
    "lapnguyen2003/traffic-sign-detection-vietnam",
    "lekimnam/roadwatch-sign-hard-negatives",
    "lekimnam/roadwatch-vietnam-sign-seed-model",
]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def list_files(reference: str, env: dict[str, str]) -> list[dict]:
    page_token: str | None = None
    files: list[dict] = []
    while True:
        command = [
            sys.executable,
            "-m",
            "kaggle",
            "datasets",
            "files",
            reference,
            "--format",
            "json",
            "--page-size",
            "200",
        ]
        if page_token:
            command.extend(["--page-token", page_token])
        completed = subprocess.run(command, capture_output=True, text=True, env=env)
        output = completed.stdout + completed.stderr
        if completed.returncode:
            raise RuntimeError(f"Cannot profile {reference}: {output[-1000:]}")
        start = output.find("[")
        end = output.rfind("]")
        if start < 0 or end < start:
            raise RuntimeError(f"Kaggle returned no JSON file list for {reference}")
        files.extend(json.loads(output[start : end + 1]))
        match = re.search(r"Next Page Token = (\S+)", output)
        page_token = match.group(1) if match else None
        if not page_token:
            return files


def main() -> int:
    values = dotenv_values(PROJECT_ROOT / ".env")
    token = values.get("KAGGLE_API_TOKEN") or values.get("KAGGLE_KEY")
    if not token:
        raise RuntimeError("Missing KAGGLE_API_TOKEN/KAGGLE_KEY in .env")
    env = os.environ.copy()
    env["KAGGLE_API_TOKEN"] = token
    rows = []
    for reference in DATASETS:
        files = list_files(reference, env)
        image_count = sum(Path(item["name"]).suffix.lower() in IMAGE_SUFFIXES for item in files)
        label_count = sum(Path(item["name"]).suffix.lower() == ".txt" for item in files)
        size_bytes = sum(int(item.get("size", 0)) for item in files)
        rows.append(
            {
                "reference": reference,
                "file_count": len(files),
                "image_count": image_count,
                "label_count": label_count,
                "size_bytes": size_bytes,
                "size_gib": round(size_bytes / 1024**3, 3),
            }
        )
    total_bytes = sum(item["size_bytes"] for item in rows)
    total_images = sum(item["image_count"] for item in rows)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "datasets": rows,
        "totals": {
            "input_size_gib": round(total_bytes / 1024**3, 3),
            "images": total_images,
            "working_disk_estimate_gib": round(max(5.0, total_bytes / 1024**3 * 2.5 + 2.0), 2),
        },
        "eta": {
            "quality_gate_minutes": [8, 25],
            "detector_training_gpu_hours_35_epochs": [2.0, 4.5],
            "speed_classifier_gpu_hours_30_epochs": [0.3, 0.8],
            "basis": "YOLO11s 640 detector plus YOLO11n-cls 160 on Kaggle T4; actual ETA depends on decoded image count and Kaggle I/O.",
        },
    }
    output = PROJECT_ROOT / "reports" / "kaggle-sign-resource-profile.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
