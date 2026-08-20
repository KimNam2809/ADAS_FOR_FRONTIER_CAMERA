"""Continue RoadWatch detector training with train-only VRU balancing."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from collections import Counter
from pathlib import Path


INPUT_ROOT = Path("/kaggle/input")
WORK_ROOT = Path("/kaggle/working")
DATASET_ROOT = WORK_ROOT / "roadwatch_balanced_dataset"
OUTPUT_ROOT = WORK_ROOT / "roadwatch_training_phase2_1"
RUN_ROOT = OUTPUT_ROOT / "roadwatch_objects_v1_1"
CANONICAL = ["person", "rider", "bicycle", "motorcycle", "car", "bus", "truck"]
ALLOWED_SOURCES = {"bdd100k", "dawn"}
EXPECTED_COUNTS = {"train": 70796, "val": 10104, "test": 20101}
REPEAT_BY_CLASS = {1: 3, 2: 2, 3: 3}
SEED = 2809


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def gpu_preflight() -> dict:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is mandatory for phase 2.1")
    devices = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    if len(devices) < 2 or not all("T4" in name.upper() for name in devices[:2]):
        raise RuntimeError(f"Phase 2.1 requires T4 x2, found {devices}")
    return {"count": len(devices), "devices": devices, "torch": torch.__version__}


def find_file(filename: str, preferred_slug: str) -> Path:
    preferred = [path for path in INPUT_ROOT.rglob(filename) if preferred_slug in str(path)]
    matches = preferred or list(INPUT_ROOT.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"Missing attached input: {filename}")
    return max(matches, key=lambda path: path.stat().st_mtime)


def resolve_image(original: str) -> Path:
    source = Path(original)
    if source.exists():
        return source
    for slug in ("bdd100k-yolo", "dawn-detection-in-adverse-weather-nature"):
        if slug not in source.parts:
            continue
        relative = Path(*source.parts[source.parts.index(slug) + 1 :])
        for root in INPUT_ROOT.rglob(slug):
            candidate = root / relative
            if candidate.exists():
                return candidate
    raise FileNotFoundError(original)


def repeat_count(record: dict) -> int:
    if record["split"] != "train":
        return 1
    classes = {int(box["class_id"]) for box in record["boxes"]}
    return max((REPEAT_BY_CLASS.get(class_id, 1) for class_id in classes), default=1)


def materialize(manifest_path: Path) -> dict:
    if DATASET_ROOT.exists():
        shutil.rmtree(DATASET_ROOT)
    original_images: Counter[str] = Counter()
    materialized_images: Counter[str] = Counter()
    original_instances: Counter[int] = Counter()
    sampled_instances: Counter[int] = Counter()
    source_counts: Counter[str] = Counter()
    multiplier_counts: Counter[int] = Counter()

    with manifest_path.open(encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if record["source"] not in ALLOWED_SOURCES:
                continue
            split = record["split"]
            if split not in EXPECTED_COUNTS:
                raise ValueError(f"Unexpected split: {split}")
            image = resolve_image(record["image"])
            repeats = repeat_count(record)
            multiplier_counts[repeats] += 1
            original_images[split] += 1
            source_counts[record["source"]] += 1
            for box in record["boxes"]:
                original_instances[int(box["class_id"])] += 1

            base_token = hashlib.sha1(
                f"{record['content_hash']}|{record['source']}|{record['image']}".encode()
            ).hexdigest()[:18]
            label_lines = [
                f"{int(box['class_id'])} "
                + " ".join(
                    f"{float(box[key]):.8f}" for key in ("cx", "cy", "width", "height")
                )
                for box in record["boxes"]
            ]
            for copy_index in range(repeats):
                token = f"{base_token}_{copy_index}"
                image_target = DATASET_ROOT / split / "images" / f"{token}{image.suffix.lower()}"
                label_target = DATASET_ROOT / split / "labels" / f"{token}.txt"
                image_target.parent.mkdir(parents=True, exist_ok=True)
                label_target.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(image, image_target)
                label_target.write_text(
                    "\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8"
                )
                materialized_images[split] += 1
                for box in record["boxes"]:
                    sampled_instances[int(box["class_id"])] += 1
            if sum(original_images.values()) % 10000 == 0:
                print(f"scanned {sum(original_images.values())} approved images", flush=True)

    actual = {split: original_images[split] for split in EXPECTED_COUNTS}
    if actual != EXPECTED_COUNTS:
        raise RuntimeError(f"Approved split drift: expected {EXPECTED_COUNTS}, got {actual}")
    if materialized_images["val"] != EXPECTED_COUNTS["val"]:
        raise RuntimeError("Validation split must never be replicated")
    if materialized_images["test"] != EXPECTED_COUNTS["test"]:
        raise RuntimeError("Test split must never be replicated")
    report = {
        "strategy": "train-only class-aware image replication",
        "repeat_by_class": {CANONICAL[key]: value for key, value in REPEAT_BY_CLASS.items()},
        "original_images": dict(original_images),
        "materialized_images": dict(materialized_images),
        "source_counts": dict(source_counts),
        "image_multiplier_counts": {str(k): v for k, v in multiplier_counts.items()},
        "original_instances": {
            CANONICAL[i]: original_instances[i] for i in range(len(CANONICAL))
        },
        "sampled_instances": {
            CANONICAL[i]: sampled_instances[i] for i in range(len(CANONICAL))
        },
        "guards": {"bard_images": 0, "val_replicated": False, "test_replicated": False},
    }
    write_json(OUTPUT_ROOT / "balance_report.json", report)
    return report


def write_yaml() -> Path:
    import yaml

    path = DATASET_ROOT / "roadwatch-balanced.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "path": str(DATASET_ROOT),
                "train": "train/images",
                "val": "val/images",
                "test": "test/images",
                "names": {i: name for i, name in enumerate(CANONICAL)},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def ensure_ultralytics() -> str:
    try:
        import ultralytics

        return ultralytics.__version__
    except ImportError:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.119"],
            check=True,
        )
        import ultralytics

        return ultralytics.__version__


def train(data_yaml: Path, checkpoint: Path) -> dict:
    from ultralytics import YOLO

    model = YOLO(str(checkpoint))
    model.train(
        data=str(data_yaml),
        epochs=20,
        imgsz=640,
        batch=64,
        device="0,1",
        workers=8,
        amp=True,
        cache=False,
        seed=SEED,
        deterministic=True,
        patience=8,
        close_mosaic=5,
        lr0=0.002,
        lrf=0.01,
        save=True,
        save_period=5,
        project=str(OUTPUT_ROOT),
        name="roadwatch_objects_v1_1",
        exist_ok=True,
        plots=True,
    )
    best = RUN_ROOT / "weights" / "best.pt"
    if not best.exists():
        raise FileNotFoundError("Training did not produce best.pt")
    metrics = YOLO(str(best)).val(
        data=str(data_yaml),
        split="test",
        imgsz=640,
        batch=64,
        device=0,
        workers=8,
        plots=True,
        project=str(OUTPUT_ROOT),
        name="roadwatch_objects_v1_1_test",
        exist_ok=True,
    )
    results = {
        key: float(value) if hasattr(value, "__float__") else value
        for key, value in metrics.results_dict.items()
    }
    write_json(OUTPUT_ROOT / "test_metrics.json", results)
    return {"best": str(best), "test_metrics": results}


def main() -> int:
    started = time.time()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    preflight = gpu_preflight()
    manifest = find_file("normalized_manifest.jsonl", "quality-gate")
    checkpoint = find_file("best.pt", "object-detector-phase-2")
    if "roadwatch_objects_v1" not in str(checkpoint):
        raise RuntimeError(f"Wrong continuation checkpoint: {checkpoint}")
    version = ensure_ultralytics()
    balance = materialize(manifest)
    data_yaml = write_yaml()
    write_json(
        OUTPUT_ROOT / "TRAINING_STATUS.json",
        {
            "status": "TRAINING",
            "gpu": preflight,
            "ultralytics": version,
            "checkpoint": str(checkpoint),
            "balance": balance,
        },
    )
    artifacts = train(data_yaml, checkpoint)
    write_json(
        OUTPUT_ROOT / "TRAINING_STATUS.json",
        {
            "status": "COMPLETE",
            "elapsed_seconds": round(time.time() - started, 2),
            "gpu": preflight,
            "ultralytics": version,
            "checkpoint": str(checkpoint),
            "balance": balance,
            "artifacts": artifacts,
        },
    )
    return 0


if __name__ == "__main__":
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as error:
        failure = {
            "status": "ERROR",
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
        write_json(OUTPUT_ROOT / "TRAINING_FAILURE.json", failure)
        print(json.dumps(failure, indent=2), file=sys.stderr, flush=True)
        raise
    finally:
        if DATASET_ROOT.exists():
            shutil.rmtree(DATASET_ROOT, ignore_errors=True)
