"""Train the RoadWatch 7-class road-user detector on approved Kaggle data."""

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
DATASET_ROOT = WORK_ROOT / "roadwatch_training_dataset"
OUTPUT_ROOT = WORK_ROOT / "roadwatch_training_output"
RUN_ROOT = OUTPUT_ROOT / "roadwatch_objects_v1"
CANONICAL = ["person", "rider", "bicycle", "motorcycle", "car", "bus", "truck"]
ALLOWED_SOURCES = {"bdd100k", "dawn"}
EXPECTED_COUNTS = {"train": 70796, "val": 10104, "test": 20101}
SEED = 2809


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def gpu_preflight() -> dict:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is mandatory for phase 2")
    devices = [torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())]
    if len(devices) < 2 or not all("T4" in name.upper() for name in devices[:2]):
        raise RuntimeError(f"RoadWatch phase 2 requires T4 x2, found {devices}")
    return {
        "count": len(devices),
        "devices": devices,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
    }


def find_quality_manifest() -> Path:
    direct = [
        INPUT_ROOT / "roadwatch-dataset-quality-gate" / "roadwatch_quality_gate" / "normalized_manifest.jsonl",
        INPUT_ROOT / "kernels" / "lekimnam" / "roadwatch-dataset-quality-gate" / "roadwatch_quality_gate" / "normalized_manifest.jsonl",
    ]
    for candidate in direct:
        if candidate.exists():
            return candidate
    likely_roots = [
        INPUT_ROOT / "kernels" / "lekimnam" / "roadwatch-dataset-quality-gate",
        INPUT_ROOT / "roadwatch-dataset-quality-gate",
    ]
    for root in likely_roots:
        if root.exists():
            matches = list(root.rglob("normalized_manifest.jsonl"))
            if matches:
                return max(matches, key=lambda path: path.stat().st_mtime)
    matches = list(INPUT_ROOT.rglob("normalized_manifest.jsonl"))
    if not matches:
        raise FileNotFoundError("Approved quality-gate manifest is not attached")
    return max(matches, key=lambda path: path.stat().st_mtime)


def resolve_image(original: str) -> Path:
    path = Path(original)
    if path.exists():
        return path
    parts = path.parts
    for slug in ("bdd100k-yolo", "dawn-detection-in-adverse-weather-nature"):
        if slug not in parts:
            continue
        offset = parts.index(slug)
        relative = Path(*parts[offset + 1 :])
        roots = [candidate for candidate in INPUT_ROOT.rglob(slug) if candidate.is_dir()]
        for root in roots:
            candidate = root / relative
            if candidate.exists():
                return candidate
    raise FileNotFoundError(original)


def materialize_approved_dataset(manifest_path: Path) -> dict:
    if DATASET_ROOT.exists():
        shutil.rmtree(DATASET_ROOT)
    counts: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    instances: Counter[int] = Counter()
    missing_images: list[str] = []
    safe_manifest = OUTPUT_ROOT / "approved_manifest.jsonl"
    safe_manifest.parent.mkdir(parents=True, exist_ok=True)

    with manifest_path.open(encoding="utf-8") as source_stream, safe_manifest.open(
        "w", encoding="utf-8"
    ) as safe_stream:
        for line in source_stream:
            record = json.loads(line)
            source = record["source"]
            if source not in ALLOWED_SOURCES:
                continue
            if source == "bard":
                raise RuntimeError("BARD quarantine guard failed")
            split = record["split"]
            if split not in EXPECTED_COUNTS:
                raise ValueError(f"Unexpected split: {split}")
            try:
                original_image = resolve_image(record["image"])
            except FileNotFoundError:
                if len(missing_images) < 20:
                    missing_images.append(record["image"])
                continue

            token = hashlib.sha1(
                f"{record['content_hash']}|{source}|{record['image']}".encode()
            ).hexdigest()[:20]
            image_name = token + original_image.suffix.lower()
            image_target = DATASET_ROOT / split / "images" / image_name
            label_target = DATASET_ROOT / split / "labels" / f"{token}.txt"
            image_target.parent.mkdir(parents=True, exist_ok=True)
            label_target.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(original_image, image_target)

            label_lines: list[str] = []
            for box in record["boxes"]:
                class_id = int(box["class_id"])
                if not 0 <= class_id < len(CANONICAL):
                    raise ValueError(f"Invalid canonical class: {class_id}")
                values = [box["cx"], box["cy"], box["width"], box["height"]]
                label_lines.append(
                    f"{class_id} " + " ".join(f"{float(value):.8f}" for value in values)
                )
                instances[class_id] += 1
            label_target.write_text(
                "\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8"
            )
            safe_stream.write(
                json.dumps(
                    {
                        "source": source,
                        "split": split,
                        "image": str(original_image),
                        "box_count": len(record["boxes"]),
                    },
                    separators=(",", ":"),
                )
                + "\n"
            )
            counts[split] += 1
            sources[source] += 1
            if sum(counts.values()) % 10000 == 0:
                print(f"materialized {sum(counts.values())} approved images", flush=True)

    if missing_images:
        raise FileNotFoundError(f"Could not resolve approved images, examples: {missing_images}")
    actual = {split: counts[split] for split in EXPECTED_COUNTS}
    if actual != EXPECTED_COUNTS:
        raise RuntimeError(f"Approved split counts changed: expected {EXPECTED_COUNTS}, got {actual}")
    if set(sources) - ALLOWED_SOURCES:
        raise RuntimeError(f"Unexpected source passed quarantine: {dict(sources)}")

    report = {
        "human_gate": "PASS: BDD100K + DAWN; BARD quarantined",
        "classes": CANONICAL,
        "images_by_split": actual,
        "images_by_source": dict(sources),
        "instances_by_class": {
            CANONICAL[index]: instances[index] for index in range(len(CANONICAL))
        },
        "bard_images": 0,
    }
    write_json(OUTPUT_ROOT / "approved_dataset_report.json", report)
    return report


def write_data_yaml() -> Path:
    import yaml

    data = {
        "path": str(DATASET_ROOT),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "names": {index: name for index, name in enumerate(CANONICAL)},
    }
    path = DATASET_ROOT / "roadwatch.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
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


def run_training(data_yaml: Path) -> dict:
    from ultralytics import YOLO

    model = YOLO("yolo11n.pt")
    model.train(
        data=str(data_yaml),
        epochs=30,
        imgsz=640,
        batch=64,
        device="0,1",
        workers=8,
        amp=True,
        cache=False,
        seed=SEED,
        deterministic=True,
        patience=10,
        close_mosaic=5,
        save=True,
        save_period=5,
        project=str(OUTPUT_ROOT),
        name="roadwatch_objects_v1",
        exist_ok=True,
        plots=True,
        verbose=True,
    )
    best = RUN_ROOT / "weights" / "best.pt"
    last = RUN_ROOT / "weights" / "last.pt"
    if not best.exists() or not last.exists():
        raise FileNotFoundError("Ultralytics did not produce best.pt and last.pt")

    test_model = YOLO(str(best))
    test_metrics = test_model.val(
        data=str(data_yaml),
        split="test",
        imgsz=640,
        batch=64,
        device=0,
        workers=8,
        plots=True,
        project=str(OUTPUT_ROOT),
        name="roadwatch_objects_v1_test",
        exist_ok=True,
    )
    results = {
        key: float(value) if hasattr(value, "__float__") else value
        for key, value in test_metrics.results_dict.items()
    }
    write_json(OUTPUT_ROOT / "test_metrics.json", results)
    return {"best": str(best), "last": str(last), "test_metrics": results}


def main() -> int:
    started = time.time()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    preflight = gpu_preflight()
    print("GPU preflight:", preflight, flush=True)
    manifest = find_quality_manifest()
    print("Approved manifest:", manifest, flush=True)
    ultralytics_version = ensure_ultralytics()
    dataset_report = materialize_approved_dataset(manifest)
    data_yaml = write_data_yaml()
    write_json(
        OUTPUT_ROOT / "TRAINING_STATUS.json",
        {
            "status": "TRAINING",
            "training_started": True,
            "gpu": preflight,
            "ultralytics": ultralytics_version,
            "dataset": dataset_report,
        },
    )
    result = run_training(data_yaml)
    write_json(
        OUTPUT_ROOT / "TRAINING_STATUS.json",
        {
            "status": "COMPLETE",
            "training_started": True,
            "elapsed_seconds": round(time.time() - started, 2),
            "gpu": preflight,
            "ultralytics": ultralytics_version,
            "dataset": dataset_report,
            "artifacts": result,
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
        # Do not persist 101k symlinks as Kaggle output. Metrics/checkpoints live
        # under OUTPUT_ROOT and remain untouched.
        if DATASET_ROOT.exists():
            shutil.rmtree(DATASET_ROOT, ignore_errors=True)
