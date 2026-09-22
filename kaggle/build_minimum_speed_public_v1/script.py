from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

INPUT = Path("/kaggle/input")
OUTPUT = Path("/kaggle/working/roadwatch_minimum_speed_public_v1")
DATASET = OUTPUT / "dataset"
SEED = 162
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")
NAMES = ["speed_limit_max", "speed_limit_min"]
MAX_IMAGE_EDGE = 1600
JPEG_QUALITY = 88
TT100K_MAX_ONLY_KEEP_PERCENT = 16
CONTENT_SPLITS: dict[str, str] = {}

# Verified against lapnguyen2003/traffic-sign-detection-vietnam/classid.xlsx.
VN_MAX_IDS = {2, 12, 39, 40, 41, 57, 58, 59, 60, 61, 62, 63}
VN_RED_RING_HARD_NEGATIVE_IDS = {
    0, 3, 4, 6, 13, 15, 17, 18, 19, 20, 21, 23, 24, 25, 26, 31, 37,
    43, 44, 45, 66, 67, 71, 74,
}

SOURCE_MANIFEST = {
    "schema_version": 1,
    "purpose": "research candidate for blue circular minimum-speed detection",
    "canonical_classes": NAMES,
    "sources": [
        {
            "slug": "braunge/tt100k",
            "upstream": "Tsinghua-Tencent 100K",
            "license": "CC BY-NC 2.0 upstream; Kaggle mirror metadata is unknown",
            "use": "minimum-speed il* signs; pm is weight restriction and excluded",
            "commercial_release": False,
        },
        {
            "slug": "lapnguyen2003/traffic-sign-detection-vietnam",
            "license": "Apache-2.0 per Kaggle metadata",
            "use": "Vietnam maximum-speed replay and red-ring hard negatives",
            "commercial_release": "verify source provenance before release",
        },
    ],
    "guardrails": [
        "No Hanoi-Hai Phong evaluation frame is included in training.",
        "Blue circular mandatory signs are not inferred as minimum speed without source labels.",
        "Red-ring prohibition signs are retained as negative images, never relabeled as speed.",
        "This dataset is research-only because TT100K is non-commercial.",
    ],
    "sampling_policy": {
        "tt100k_minimum_speed": "keep_all",
        "tt100k_maximum_speed_only": f"deterministic_{TT100K_MAX_ONLY_KEEP_PERCENT}_percent",
        "vietnam_maximum_speed": "keep_all",
        "vietnam_red_ring_hard_negative": "deterministic_shuffle_max_800",
        "image_encoding": f"jpeg_quality_{JPEG_QUALITY}_max_edge_{MAX_IMAGE_EDGE}",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_names(yaml_path: Path) -> list[str]:
    payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    names = payload.get("names", [])
    if isinstance(names, dict):
        return [str(names[key]) for key in sorted(names, key=lambda item: int(item))]
    return [str(item) for item in names]


def find_image(label: Path) -> Path | None:
    candidates: list[Path] = []
    parts = list(label.parts)
    for token in ("labels", "label"):
        if token in parts:
            swapped = list(parts)
            swapped[swapped.index(token)] = "images"
            base = Path(*swapped).with_suffix("")
            candidates.extend(base.with_suffix(suffix) for suffix in IMAGE_SUFFIXES)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def split_for(source: str, image: Path) -> str:
    # Keep duplicate-looking TT100K derivatives together to reduce leakage.
    group = re.sub(r"\s*\(\d+\)$", "", image.stem)
    source = "vietnam" if source.startswith("vietnam") else source
    # Vietnam images are extracted video-like sequences. Keep adjacent frame IDs
    # together so highly similar neighbouring frames cannot cross the split.
    if source == "vietnam" and group.isdigit():
        group = f"sequence_{int(group) // 50:06d}"
    bucket = int(hashlib.sha1(f"{source}:{group}".encode()).hexdigest()[:8], 16) % 10
    return "val" if bucket < 2 else "train"


def deterministic_percent(source: str, image: Path) -> int:
    group = re.sub(r"\s*\(\d+\)$", "", image.stem)
    return int(hashlib.sha1(f"{source}:{group}".encode()).hexdigest()[:8], 16) % 100


def parse_rows(path: Path) -> list[tuple[int, list[float]]]:
    rows: list[tuple[int, list[float]]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        fields = raw.split()
        if len(fields) != 5:
            continue
        try:
            class_id = int(float(fields[0]))
            box = [float(value) for value in fields[1:]]
        except ValueError:
            continue
        if all(0.0 <= value <= 1.0 for value in box) and box[2] > 0 and box[3] > 0:
            rows.append((class_id, box))
    return rows


def write_sample(
    source: str,
    image: Path,
    boxes: list[tuple[int, list[float]]],
    *,
    negative: bool = False,
) -> dict[str, object]:
    source_hash = hashlib.sha1(str(image).encode()).hexdigest()[:12]
    stem = f"{source}_{source_hash}_{re.sub(r'[^A-Za-z0-9_-]+', '_', image.stem)[:60]}"
    # Normalized YOLO coordinates remain valid after proportional resizing. JPEG
    # output prevents the large TT100K PNG corpus from exhausting Kaggle storage.
    with Image.open(image).convert("RGB") as source_image:
        source_image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
        content_key = hashlib.sha256(
            f"{source_image.size}:{source_image.mode}".encode() + source_image.tobytes()
        ).hexdigest()
        proposed_split = split_for(source, image)
        split = CONTENT_SPLITS.setdefault(content_key, proposed_split)
        image_target = DATASET / "images" / split / f"{stem}.jpg"
        label_target = DATASET / "labels" / split / f"{stem}.txt"
        image_target.parent.mkdir(parents=True, exist_ok=True)
        label_target.parent.mkdir(parents=True, exist_ok=True)
        source_image.save(image_target, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    label_target.write_text(
        "\n".join(
            f"{class_id} " + " ".join(f"{value:.8f}" for value in box)
            for class_id, box in boxes
        ) + ("\n" if boxes else ""),
        encoding="utf-8",
    )
    return {
        "source": source,
        "source_image": str(image),
        "split": split,
        "image": str(image_target.relative_to(OUTPUT)),
        "label": str(label_target.relative_to(OUTPUT)),
        "instances": [NAMES[class_id] for class_id, _ in boxes],
        "hard_negative": negative,
        "sha256": sha256(image_target),
    }


def collect_tt100k() -> list[dict[str, object]]:
    yaml_paths = sorted(INPUT.rglob("*TT100K.yaml"))
    if not yaml_paths:
        yaml_paths = [
            path for path in INPUT.rglob("*.yaml")
            if "pm" in path.read_text(encoding="utf-8", errors="ignore")
            and "pl80" in path.read_text(encoding="utf-8", errors="ignore")
        ]
    if not yaml_paths:
        mounted = sorted(str(path) for path in INPUT.glob("*"))
        raise RuntimeError(f"TT100K YAML not found; mounted inputs={mounted}")
    root = yaml_paths[-1].parent
    names = read_names(yaml_paths[-1])
    minimum_ids = {idx for idx, name in enumerate(names) if re.fullmatch(r"il\d+", name)}
    maximum_ids = {idx for idx, name in enumerate(names) if re.fullmatch(r"pl\d+", name)}
    if not minimum_ids or not maximum_ids:
        raise RuntimeError(f"TT100K speed classes missing: min={minimum_ids}, max={maximum_ids}")
    records = []
    for label in root.rglob("*.txt"):
        if "label" not in {part.lower() for part in label.parts} and "labels" not in {part.lower() for part in label.parts}:
            continue
        rows = parse_rows(label)
        mapped = []
        for class_id, box in rows:
            if class_id in maximum_ids:
                mapped.append((0, box))
            elif class_id in minimum_ids:
                mapped.append((1, box))
        if not mapped:
            continue
        image = find_image(label)
        # Preserve every rare minimum-speed image and downsample only max-speed
        # replay so the candidate is not dominated by the already-solved class.
        has_minimum = any(class_id == 1 for class_id, _ in mapped)
        if image and (
            has_minimum
            or deterministic_percent("tt100k_max_only", image) < TT100K_MAX_ONLY_KEEP_PERCENT
        ):
            records.append(write_sample("tt100k", image, mapped))
    if not any("speed_limit_min" in record["instances"] for record in records):
        raise RuntimeError("No TT100K minimum-speed samples were exported")
    return records


def collect_vietnam() -> list[dict[str, object]]:
    class_files = sorted(INPUT.rglob("classid.xlsx"))
    if len(class_files) != 1:
        mounted = sorted(str(path) for path in INPUT.glob("*"))
        raise RuntimeError(f"Expected one Vietnam classid.xlsx, found {class_files}; mounted={mounted}")
    root = class_files[0].parent
    positives: list[dict[str, object]] = []
    negative_candidates: list[tuple[Path, list[tuple[int, list[float]]]]] = []
    for label in root.rglob("*.txt"):
        if "label" not in {part.lower() for part in label.parts} and "labels" not in {part.lower() for part in label.parts}:
            continue
        rows = parse_rows(label)
        image = find_image(label)
        if not image:
            continue
        speed_boxes = [(0, box) for class_id, box in rows if class_id in VN_MAX_IDS]
        if speed_boxes:
            positives.append(write_sample("vietnam", image, speed_boxes))
        elif rows and any(class_id in VN_RED_RING_HARD_NEGATIVE_IDS for class_id, _ in rows):
            negative_candidates.append((image, rows))
    random.Random(SEED).shuffle(negative_candidates)
    # A bounded replay of red-ring non-speed signs directly addresses the observed
    # CVAT false-positive mode without overwhelming the two positive classes.
    negative_limit = min(800, len(negative_candidates))
    negatives = [
        write_sample("vietnam_negative", image, [], negative=True)
        for image, _ in negative_candidates[:negative_limit]
    ]
    if not positives:
        raise RuntimeError("No Vietnamese maximum-speed replay samples were exported")
    return positives + negatives


def contact_sheet(records: list[dict[str, object]], split: str, class_name: str) -> None:
    selected = [
        record for record in records
        if record["split"] == split and class_name in record["instances"]
    ][:48]
    if not selected:
        return
    tile = 240
    columns = 6
    rows = (len(selected) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * tile, rows * tile), "black")
    for index, record in enumerate(selected):
        image_path = OUTPUT / str(record["image"])
        label_path = OUTPUT / str(record["label"])
        with Image.open(image_path).convert("RGB") as original:
            width, height = original.size
            canvas = original.copy()
        draw = ImageDraw.Draw(canvas)
        for raw in label_path.read_text(encoding="utf-8").splitlines():
            class_id, cx, cy, bw, bh = [float(value) for value in raw.split()]
            x1, y1 = (cx - bw / 2) * width, (cy - bh / 2) * height
            x2, y2 = (cx + bw / 2) * width, (cy + bh / 2) * height
            draw.rectangle((x1, y1, x2, y2), outline="cyan" if int(class_id) else "red", width=max(2, width // 600))
        canvas.thumbnail((tile, tile))
        x = (index % columns) * tile + (tile - canvas.width) // 2
        y = (index // columns) * tile + (tile - canvas.height) // 2
        sheet.paste(canvas, (x, y))
    review = OUTPUT / "quality_gate"
    review.mkdir(parents=True, exist_ok=True)
    sheet.save(review / f"{split}_{class_name}.jpg", quality=90)


def main() -> None:
    records = collect_tt100k() + collect_vietnam()
    counts = Counter()
    image_counts = Counter()
    for record in records:
        image_counts[str(record["split"])] += 1
        for name in record["instances"]:
            counts[f"{record['split']}:{name}"] += 1
    data = {
        "path": ".",
        "train": "images/train",
        "val": "images/val",
        "names": {index: name for index, name in enumerate(NAMES)},
    }
    (DATASET / "data.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    (OUTPUT / "source_manifest.json").write_text(
        json.dumps(SOURCE_MANIFEST, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUTPUT / "sample_manifest.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    audit = {
        "status": "READY_FOR_HUMAN_QUALITY_GATE",
        "images": dict(image_counts),
        "instances": dict(counts),
        "hard_negative_images": sum(bool(record["hard_negative"]) for record in records),
        "minimum_speed_train_instances": counts["train:speed_limit_min"],
        "minimum_speed_val_instances": counts["val:speed_limit_min"],
        "license_release_scope": "research-only",
    }
    if audit["minimum_speed_train_instances"] < 20 or audit["minimum_speed_val_instances"] < 5:
        raise RuntimeError(f"Insufficient minimum-speed coverage: {audit}")
    (OUTPUT / "dataset_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    for split in ("train", "val"):
        for class_name in NAMES:
            contact_sheet(records, split, class_name)
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
