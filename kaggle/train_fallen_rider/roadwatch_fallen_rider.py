"""Quality-gated fallen-person/rider specialist training for Kaggle GPU."""

from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import cv2
import yaml


INPUT = Path("/kaggle/input")
OUTPUT = Path("/kaggle/working/roadwatch_fallen_rider")
TARGET_NAMES = ["fallen_person", "fallen_rider"]
SEED = 2809


def write_json(name: str, payload: object) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def gpu_preflight() -> dict:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("Kaggle GPU is mandatory")
    return {
        "devices": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
        "torch": torch.__version__,
    }


def names_from_yaml(data: dict) -> list[str]:
    names = data.get("names", [])
    if isinstance(names, dict):
        normalized = {int(key): str(value) for key, value in names.items()}
        return [normalized[index] for index in sorted(normalized)]
    return [str(value) for value in names]


def resolve_images(yaml_path: Path, data: dict, split: str) -> list[Path]:
    value = data.get(split)
    if not value:
        return []
    root = Path(data.get("path", yaml_path.parent))
    if not root.is_absolute():
        root = (yaml_path.parent / root).resolve()
    elif root == Path("/") or not root.exists():
        # Public exports often preserve `path: /` from their original
        # workstation. On Kaggle the actual root is the YAML directory.
        root = yaml_path.parent
    result: list[Path] = []
    for raw in value if isinstance(value, list) else [value]:
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        if path.is_dir():
            result.extend(p for p in path.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        elif path.is_file():
            result.extend(Path(row.strip()) for row in path.read_text().splitlines() if row.strip())
    return result


def label_path(image: Path) -> Path:
    parts = list(image.parts)
    if "images" in parts:
        parts[parts.index("images")] = "labels"
    return Path(*parts).with_suffix(".txt")


def audit_dataset(yaml_path: Path) -> dict:
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    names = names_from_yaml(data)
    counts: Counter[int] = Counter()
    images_by_split: dict[str, int] = {}
    negatives = 0
    invalid = 0
    hashes_by_split: dict[str, set[str]] = {}
    previews: list[tuple[Path, list[list[str]]]] = []
    for split in ("train", "val", "test"):
        images = resolve_images(yaml_path, data, split)
        images_by_split[split] = len(images)
        hashes_by_split[split] = set()
        for image in images:
            try:
                hashes_by_split[split].add(hashlib.sha256(image.read_bytes()).hexdigest())
            except OSError:
                invalid += 1
                continue
            labels = label_path(image)
            rows = [row.split() for row in labels.read_text().splitlines() if row.strip()] if labels.exists() else []
            if not rows:
                negatives += 1
            for row in rows:
                if len(row) < 5:
                    invalid += 1
                    continue
                class_id = int(float(row[0]))
                if class_id < 0 or class_id >= len(names):
                    invalid += 1
                    continue
                counts[class_id] += 1
            if rows and len(previews) < 40:
                previews.append((image, rows))
    leakage = {
        "train_val": len(hashes_by_split["train"] & hashes_by_split["val"]),
        "train_test": len(hashes_by_split["train"] & hashes_by_split["test"]),
        "val_test": len(hashes_by_split["val"] & hashes_by_split["test"]),
    }
    review = OUTPUT / "quality_gate_samples"
    review.mkdir(parents=True, exist_ok=True)
    random.Random(SEED).shuffle(previews)
    for index, (image, rows) in enumerate(previews[:20]):
        frame = cv2.imread(str(image))
        if frame is None:
            continue
        height, width = frame.shape[:2]
        for row in rows:
            if len(row) < 5:
                continue
            class_id = int(float(row[0]))
            cx, cy, bw, bh = map(float, row[1:5])
            x1, y1 = int((cx - bw / 2) * width), int((cy - bh / 2) * height)
            x2, y2 = int((cx + bw / 2) * width), int((cy + bh / 2) * height)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 255), 2)
            cv2.putText(frame, names[class_id], (x1, max(20, y1 - 5)), 0, 0.55, (0, 220, 255), 2)
        cv2.imwrite(str(review / f"sample_{index:02d}.jpg"), frame)
    return {
        "yaml": str(yaml_path),
        "names": names,
        "images": images_by_split,
        "instances": {names[key]: value for key, value in counts.items()},
        "negative_images": negatives,
        "invalid_rows_or_files": invalid,
        "hash_leakage": leakage,
    }


def main() -> int:
    write_json("gpu.json", gpu_preflight())
    yaml_candidates = list(INPUT.rglob("*.yaml")) + list(INPUT.rglob("*.yml"))
    audits = [audit_dataset(path) for path in yaml_candidates]
    target = next((item for item in audits if item["names"] == TARGET_NAMES), None)
    gate = {
        "audits": audits,
        "target_taxonomy_exact": target is not None,
        "minimum_instances": bool(target) and all(target["instances"].get(name, 0) >= 250 for name in TARGET_NAMES),
        "negative_images_present": bool(target) and target["negative_images"] >= 500,
        "no_hash_leakage": bool(target) and not any(target["hash_leakage"].values()),
        "target_dashcam_domain": os.getenv("TARGET_DASHCAM_DOMAIN_CONFIRMED", "0") == "1",
        "license_reviewed": os.getenv("DATASET_LICENSE_APPROVED", "0") == "1",
    }
    gate["passed"] = all(value for key, value in gate.items() if key not in {"audits", "passed"})
    write_json("quality_gate.json", gate)
    if not gate["passed"] or os.getenv("QUALITY_GATE_APPROVED", "0") != "1":
        write_json("status.json", {"status": "WAITING_FOR_HUMAN_QUALITY_GATE"})
        return 0
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics>=8.3,<9"], check=True)
    from ultralytics import YOLO

    model = YOLO("yolo11n.pt")
    result = model.train(
        data=target["yaml"], epochs=45, imgsz=640, batch=16, device=0,
        project=str(OUTPUT), name="fallen_detector", seed=SEED, patience=10,
    )
    best = Path(result.save_dir) / "weights" / "best.pt"
    shutil.copy2(best, OUTPUT / "roadwatch_fallen_rider_v1.pt")
    YOLO(str(best)).export(format="onnx", imgsz=640, simplify=True)
    write_json("status.json", {"status": "TRAINING_COMPLETE"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
