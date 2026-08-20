"""RoadWatch Kaggle phase 1: normalize and audit; never train.

The script is designed for a private Kaggle Script kernel with BDD100K YOLO, BARD,
and DAWN attached as read-only inputs. All outputs are compact manifests/reports and
visual samples under /kaggle/working/roadwatch_quality_gate.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import time
import traceback
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


CANONICAL = ["person", "rider", "bicycle", "motorcycle", "car", "bus", "truck"]
ALIASES = {
    "person": "person",
    "pedestrian": "person",
    "rider": "rider",
    "cyclist": "rider",
    "bike": "bicycle",
    "bicycle": "bicycle",
    "motor": "motorcycle",
    "motorbike": "motorcycle",
    "motorcycle": "motorcycle",
    "car": "car",
    "bus": "bus",
    "truck": "truck",
}
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
INPUT_ROOT = Path("/kaggle/input")
OUTPUT_ROOT = Path("/kaggle/working/roadwatch_quality_gate")
SEED = 2809


@dataclass
class Box:
    class_id: int
    cx: float
    cy: float
    width: float
    height: float


@dataclass
class Record:
    source: str
    image: str
    split: str
    boxes: list[Box]
    content_hash: str = ""


def normalized_name(value: object) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def canonical_id(name: object) -> int | None:
    key = normalized_name(name)
    canonical = ALIASES.get(key)
    return CANONICAL.index(canonical) if canonical in CANONICAL else None


def yaml_names(path: Path) -> dict[int, str]:
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        names = data.get("names", {})
        if isinstance(names, list):
            return {index: str(name) for index, name in enumerate(names)}
        return {int(index): str(name) for index, name in names.items()}
    except Exception:
        return {}


def find_class_map(root: Path, fallback: dict[int, str]) -> tuple[dict[int, int], str | None]:
    for candidate in sorted(root.rglob("*.yaml")) + sorted(root.rglob("*.yml")):
        names = yaml_names(candidate)
        if names:
            mapped = {old: new for old, name in names.items() if (new := canonical_id(name)) is not None}
            if mapped:
                return mapped, str(candidate)
    return (
        {old: new for old, name in fallback.items() if (new := canonical_id(name)) is not None},
        None,
    )


def infer_split(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    if "test" in parts:
        return "test"
    if "val" in parts or "valid" in parts or "validation" in parts:
        return "val"
    if "train" in parts:
        return "train"
    digest = int(hashlib.sha1(path.stem.encode()).hexdigest()[:8], 16) % 100
    return "train" if digest < 80 else "val" if digest < 90 else "test"


def label_candidates(image: Path, root: Path, label_index: dict[str, list[Path]]) -> Iterable[Path]:
    relative = image.relative_to(root)
    parts = list(relative.parts)
    for index, part in enumerate(parts):
        if part.lower() == "images":
            replaced = parts.copy()
            replaced[index] = "labels"
            yield root.joinpath(*replaced).with_suffix(".txt")
    yield image.with_suffix(".txt")
    for candidate in label_index.get(image.stem.lower(), []):
        yield candidate


def parse_yolo(path: Path, class_map: dict[int, int]) -> tuple[list[Box], int]:
    boxes: list[Box] = []
    invalid = 0
    if not path.exists():
        return boxes, invalid
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        fields = line.split()
        if len(fields) < 5:
            invalid += 1
            continue
        try:
            old_id = int(float(fields[0]))
            coords = [float(value) for value in fields[1:5]]
        except ValueError:
            invalid += 1
            continue
        new_id = class_map.get(old_id)
        if new_id is None:
            continue
        cx, cy, width, height = coords
        if not all(0.0 <= value <= 1.0 for value in (cx, cy, width, height)) or width <= 0 or height <= 0:
            invalid += 1
            continue
        boxes.append(Box(new_id, cx, cy, width, height))
    return boxes, invalid


def scan_yolo(source: str, root: Path, fallback: dict[int, str]) -> tuple[list[Record], dict]:
    class_map, yaml_path = find_class_map(root, fallback)
    labels = list(root.rglob("*.txt"))
    label_index: dict[str, list[Path]] = defaultdict(list)
    for label in labels:
        label_index[label.stem.lower()].append(label)
    records: list[Record] = []
    missing_labels = invalid_boxes = 0
    images = [path for path in root.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES]
    for image in images:
        label = next((item for item in label_candidates(image, root, label_index) if item.exists()), None)
        if label is None:
            missing_labels += 1
            boxes = []
        else:
            boxes, invalid = parse_yolo(label, class_map)
            invalid_boxes += invalid
        records.append(Record(source, str(image), infer_split(image), boxes))
    return records, {
        "source": source,
        "images": len(images),
        "labels": len(labels),
        "missing_labels": missing_labels,
        "invalid_boxes": invalid_boxes,
        "yaml": yaml_path,
        "class_map": class_map,
    }


def parse_voc(xml_path: Path, image_path: Path) -> tuple[list[Box], int]:
    boxes: list[Box] = []
    invalid = 0
    try:
        root = ET.parse(xml_path).getroot()
        width = float(root.findtext("size/width", "0"))
        height = float(root.findtext("size/height", "0"))
        if width <= 0 or height <= 0:
            with Image.open(image_path) as image:
                width, height = image.size
        for obj in root.findall("object"):
            class_id = canonical_id(obj.findtext("name", ""))
            bounds = obj.find("bndbox")
            if class_id is None or bounds is None:
                continue
            xmin = float(bounds.findtext("xmin", "0"))
            ymin = float(bounds.findtext("ymin", "0"))
            xmax = float(bounds.findtext("xmax", "0"))
            ymax = float(bounds.findtext("ymax", "0"))
            if xmax <= xmin or ymax <= ymin:
                invalid += 1
                continue
            boxes.append(Box(class_id, (xmin + xmax) / (2 * width), (ymin + ymax) / (2 * height), (xmax - xmin) / width, (ymax - ymin) / height))
    except Exception:
        invalid += 1
    return boxes, invalid


def scan_dawn(root: Path) -> tuple[list[Record], dict]:
    images = [path for path in root.rglob("*") if path.suffix.lower() in IMAGE_SUFFIXES]
    by_stem: dict[str, list[Path]] = defaultdict(list)
    for xml_path in root.rglob("*.xml"):
        by_stem[xml_path.stem.lower()].append(xml_path)
    records: list[Record] = []
    missing_labels = invalid_boxes = 0
    for image in images:
        choices = by_stem.get(image.stem.lower(), [])
        if not choices:
            missing_labels += 1
            boxes = []
        else:
            boxes, invalid = parse_voc(choices[0], image)
            invalid_boxes += invalid
        records.append(Record("dawn", str(image), infer_split(image), boxes))
    return records, {
        "source": "dawn",
        "images": len(images),
        "labels": sum(len(items) for items in by_stem.values()),
        "missing_labels": missing_labels,
        "invalid_boxes": invalid_boxes,
    }


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deduplicate(records: list[Record]) -> tuple[list[Record], dict]:
    # Complete annotations outrank vehicle-only BARD copies.
    priority = {"bdd100k": 3, "dawn": 2, "bard": 1}
    # Hashing every image made the first gate unnecessarily expensive. BDD/BARD
    # preserve source filenames, so first group by basename + exact byte size and
    # only calculate SHA-256 inside possible duplicate groups.
    candidates: dict[tuple[str, int], list[Record]] = defaultdict(list)
    for record in records:
        path = Path(record.image)
        candidates[(path.name.lower(), path.stat().st_size)].append(record)

    by_hash: dict[str, Record] = {}
    duplicate_sources: Counter[str] = Counter()
    hashed_files = 0
    for index, (signature, group) in enumerate(candidates.items(), start=1):
        if len(group) == 1:
            record = group[0]
            record.content_hash = "signature:" + hashlib.sha1(
                f"{signature[0]}:{signature[1]}".encode()
            ).hexdigest()
            by_hash[record.content_hash] = record
            continue
        for record in group:
            record.content_hash = sha256(record.image)
            hashed_files += 1
            previous = by_hash.get(record.content_hash)
            if previous is None or priority[record.source] > priority[previous.source]:
                if previous is not None:
                    duplicate_sources[f"{previous.source}->{record.source}"] += 1
                    record.split = previous.split if previous.source == "bdd100k" else record.split
                by_hash[record.content_hash] = record
            else:
                duplicate_sources[f"{record.source}->{previous.source}"] += 1
        if index % 10000 == 0:
            print(f"checked {index}/{len(candidates)} filename-size groups", flush=True)
    unique = list(by_hash.values())
    split_hashes: dict[str, set[str]] = defaultdict(set)
    for record in unique:
        split_hashes[record.split].add(record.content_hash)
    leakage = {
        "train_val": len(split_hashes["train"] & split_hashes["val"]),
        "train_test": len(split_hashes["train"] & split_hashes["test"]),
        "val_test": len(split_hashes["val"] & split_hashes["test"]),
    }
    return unique, {
        "input_records": len(records),
        "unique_images": len(unique),
        "duplicates_removed": len(records) - len(unique),
        "sha256_files": hashed_files,
        "candidate_strategy": "same lowercase basename and exact byte size, then SHA-256",
        "duplicate_precedence": dict(duplicate_sources),
        "split_leakage_after_dedup": leakage,
    }


def draw_record(record: Record, destination: Path) -> None:
    with Image.open(record.image) as source:
        image = source.convert("RGB")
    image.thumbnail((1280, 720))
    draw = ImageDraw.Draw(image)
    width, height = image.size
    colors = ["#00d4ff", "#ffd166", "#06d6a0", "#ef476f", "#118ab2", "#8338ec", "#ff9f1c"]
    for box in record.boxes:
        x1 = (box.cx - box.width / 2) * width
        y1 = (box.cy - box.height / 2) * height
        x2 = (box.cx + box.width / 2) * width
        y2 = (box.cy + box.height / 2) * height
        color = colors[box.class_id]
        draw.rectangle((x1, y1, x2, y2), outline=color, width=3)
        draw.text((x1 + 3, max(0, y1 - 14)), CANONICAL[box.class_id], fill=color)
    draw.rectangle((0, 0, width, 24), fill="#001f3f")
    draw.text((8, 5), f"{record.source} | {record.split} | boxes={len(record.boxes)}", fill="white")
    image.save(destination, quality=88)


def write_outputs(records: list[Record], source_reports: list[dict], dedup_report: dict, elapsed: float) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    class_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    for record in records:
        source_counts[record.source] += 1
        split_counts[record.split] += 1
        for box in record.boxes:
            class_counts[CANONICAL[box.class_id]] += 1
    report = {
        "canonical_classes": CANONICAL,
        "source_scan": source_reports,
        "deduplication": dedup_report,
        "unique_images_by_source": dict(source_counts),
        "unique_images_by_split": dict(split_counts),
        "instances_by_class": dict(class_counts),
        "elapsed_seconds": round(elapsed, 2),
    }
    (OUTPUT_ROOT / "dataset_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    manifest = OUTPUT_ROOT / "normalized_manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(asdict(record), separators=(",", ":")) + "\n")

    candidates = [record for record in records if record.boxes]
    rng = random.Random(SEED)
    rng.shuffle(candidates)
    audit_dir = OUTPUT_ROOT / "audit_samples"
    audit_dir.mkdir(exist_ok=True)
    selected: list[Record] = []
    per_source: Counter[str] = Counter()
    for record in candidates:
        if per_source[record.source] < 8:
            selected.append(record)
            per_source[record.source] += 1
        if len(selected) >= 24:
            break
    for index, record in enumerate(selected):
        draw_record(record, audit_dir / f"{index:02d}_{record.source}.jpg")

    gate = {
        "status": "PENDING_HUMAN_REVIEW",
        "training_started": False,
        "required_action": "Inspect dataset_audit.json and audit_samples, then tell RoadWatch agent PASS or FAIL.",
        "sample_count": len(selected),
    }
    (OUTPUT_ROOT / "QUALITY_GATE_STATUS.json").write_text(json.dumps(gate, indent=2), encoding="utf-8")
    print(json.dumps(gate, indent=2))


def gpu_preflight() -> dict:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("GPU is mandatory, but CUDA is not available")
    devices = [torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())]
    if not all("T4" in name.upper() for name in devices):
        raise RuntimeError(f"Expected Kaggle T4 accelerator, found {devices}")
    return {"count": len(devices), "devices": devices, "torch": torch.__version__}


def input_inventory(root: Path, max_depth: int = 5, limit: int = 200) -> list[str]:
    """Return a compact directory inventory without walking every dataset file."""
    if not root.exists():
        return [f"{root} does not exist"]
    inventory: list[str] = []
    pending: list[tuple[Path, int]] = [(root, 0)]
    while pending and len(inventory) < limit:
        current, depth = pending.pop(0)
        try:
            children = sorted(
                (child for child in current.iterdir() if child.is_dir()),
                key=lambda child: child.name.lower(),
            )
        except OSError as error:
            inventory.append(f"{current} [unreadable: {error}]")
            continue
        for child in children:
            inventory.append(str(child))
            if depth + 1 < max_depth:
                pending.append((child, depth + 1))
            if len(inventory) >= limit:
                break
    return inventory


def discover_dataset_root(slug: str, owner: str) -> Path:
    """Support both legacy and current Kaggle input mount layouts."""
    direct_candidates = [
        INPUT_ROOT / slug,
        INPUT_ROOT / "datasets" / owner / slug,
    ]
    for candidate in direct_candidates:
        if candidate.exists():
            return candidate

    if INPUT_ROOT.exists():
        matches = [
            path
            for path in INPUT_ROOT.rglob(slug)
            if path.is_dir() and path.name.lower() == slug.lower()
        ]
        if matches:
            return min(matches, key=lambda path: (len(path.parts), str(path)))
    raise FileNotFoundError(f"Cannot discover Kaggle dataset mount for {owner}/{slug}")


def main() -> int:
    started = time.time()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "runtime.log").write_text("RoadWatch quality gate started\n", encoding="utf-8")
    print("GPU preflight:", gpu_preflight(), flush=True)
    inventory = input_inventory(INPUT_ROOT)
    (OUTPUT_ROOT / "input_inventory.json").write_text(
        json.dumps(inventory, indent=2), encoding="utf-8"
    )
    print("Kaggle input mount inventory:", json.dumps(inventory[:40], indent=2), flush=True)
    roots = {
        "bdd100k": discover_dataset_root("bdd100k-yolo", "a7madmostafa"),
        "bard": discover_dataset_root("bard-vehicle-detection", "mingshen0118"),
        "dawn": discover_dataset_root(
            "dawn-detection-in-adverse-weather-nature", "orvile"
        ),
    }
    print("Discovered dataset roots:", {key: str(value) for key, value in roots.items()}, flush=True)

    bdd, bdd_report = scan_yolo(
        "bdd100k",
        roots["bdd100k"],
        {0: "person", 1: "rider", 2: "car", 3: "bus", 4: "truck", 5: "bike", 6: "motor"},
    )
    bard, bard_report = scan_yolo(
        "bard",
        roots["bard"],
        # BARD ships without data.yaml. Its six source IDs are alphabetically
        # ordered: bicycle, bus, car, motorcycle, train, truck.
        {0: "bicycle", 1: "bus", 2: "car", 3: "motorcycle", 4: "train", 5: "truck"},
    )
    dawn, dawn_report = scan_dawn(roots["dawn"])
    (OUTPUT_ROOT / "source_scan.json").write_text(
        json.dumps([bdd_report, bard_report, dawn_report], indent=2), encoding="utf-8"
    )
    records, dedup_report = deduplicate(bdd + bard + dawn)
    write_outputs(records, [bdd_report, bard_report, dawn_report], dedup_report, time.time() - started)
    print("QUALITY GATE reached. No training code was executed.")
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
        (OUTPUT_ROOT / "FAILURE.json").write_text(
            json.dumps(failure, indent=2), encoding="utf-8"
        )
        print(json.dumps(failure, indent=2), file=sys.stderr, flush=True)
        raise
