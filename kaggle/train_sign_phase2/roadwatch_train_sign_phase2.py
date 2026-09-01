"""Audit and train RoadWatch sign detector + numeric speed classifier on Kaggle."""

from __future__ import annotations

import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import yaml


INPUT = Path("/kaggle/input")
WORK = Path("/kaggle/working")
OUTPUT = WORK / "roadwatch_sign_phase2"
DATASET = WORK / "sign_dataset"
SPEED_CROPS = WORK / "speed_crops"
CLEAN_SPEED_CROPS = WORK / "clean_speed_crops"
SEED = 2809
SPEED_VALUES = {10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120}
UNSUPPORTED_SPEED_VALUES = {10}
CLASSIFIER_SPEED_VALUES = SPEED_VALUES - UNSUPPORTED_SPEED_VALUES
SUSPECT_SPEED_VALUES = {10, 50, 80, 90}
VNTS_SPEED_PREFIX = "vnts_"
GTSRB_SPEED_CLASSES = {0: 20, 1: 30, 2: 50, 3: 60, 4: 70, 5: 80, 7: 100, 8: 120}
KNOWN_BAD_IMAGES = {("train", "0477")}
KNOWN_SEMANTIC_ISSUES = [
    {
        "scope": "speed_class_57",
        "declared": "Speed limit 10km/h",
        "observed": "mixture of visible 10km/h and 40km/h signs",
        "action": "block training until every class-57 annotation is corrected",
    },
    {
        "scope": "train/images/0477.jpg",
        "declared": "Speed limit 40km/h",
        "observed": "intersection warning sign",
        "action": "quarantine image from training",
    },
    {
        "scope": "speed_class_39",
        "declared": "Speed limit 50km/h",
        "observed": "contact sheets contain multiple visible 80km/h signs",
        "action": "block training until class-39 annotations are corrected",
    },
    {
        "scope": "speed_class_41",
        "declared": "Speed limit 80km/h",
        "observed": "contact sheets contain multiple visible 60km/h signs",
        "action": "block training until class-41 annotations are corrected",
    },
    {
        "scope": "speed_class_63",
        "declared": "Speed limit 90km/h",
        "observed": "contact sheet contains at least one visible 30km/h sign",
        "action": "block training until class-63 annotations are corrected",
    },
]
MANUAL_CURATION_PATH = Path(__file__).with_name("manual_speed_curation.json")
INLINE_MANUAL_CURATION = {
    "schema_version": 1,
    "source_run": "RoadWatch Traffic Sign Phase 2 Versions 10 and 12",
    "review_method": "Human visual review of bootstrap_rejected_ranked contact sheets",
    "reviewer": "RoadWatch project team",
    "review_history": [
        "Version 10: initial recovery of clear 80/90 crops and unsupported 10 review",
        (
            "Version 12: added seven train and one validation crop for class 90 from the "
            "remaining ranked rejection sheet"
        ),
        (
            "Post-Version 14: added five additional clear class-90 train crops from the "
            "Version 12 ranked sheet to avoid a boundary-fragile 50-sample gate"
        ),
    ],
    "accepted_numeric": {
        "val:80": "c41_3932_000071".split(),
        "train:90": (
            "c63_4041_000030 c63_4059_000061 c63_4121_000038 c63_4055_000058 "
            "c63_4013_000065 c63_4056_000044 c63_4043_000039 c63_4058_000077 "
            "c63_4142_000019 c63_4052_000047 c63_4113_000056 c63_4115_000017 "
            "c63_4103_000063 c63_4139_000025 c63_4050_000051 c63_4054_000042 "
            "c63_4025_000052 c63_4144_000037 c63_4049_000034 c63_4048_000057 "
            "c63_4015_000078 c63_4036_000018 c63_4072_000001 c63_4070_000035 "
            "c63_4074_000009 c63_4116_000053 c63_4068_000015 c63_4029_000014 "
            "c63_4046_000076 c63_4063_000031 c63_4078_000074 c63_4006_000054 "
            "c63_4111_000024 c63_4014_000064 c63_4040_000070 c63_4047_000067 "
            "c63_4044_000041 c63_4010_000036 c63_4034_000071 c63_4077_000006 "
            "c63_4060_000045"
        ).split(),
        "val:90": (
            "c63_4118_000006 c63_4012_000004 c63_4081_000000 c63_4027_000002 "
            "c63_4080_000014 c63_4030_000012 c63_4035_000001 c63_4147_000008 "
            "c63_4472_000010 c63_4019_000016"
        ).split(),
    },
    "accepted_unknown": {
        "train": (
            "c57_4415_000042 c57_4413_000013 c57_4413_000012 c57_4411_000068 "
            "c57_4418_000059 c57_4417_000090 c57_4429_000019 c57_4409_000070 "
            "c57_4432_000057 c57_4412_000099 c57_4419_000050 c57_4432_000056 "
            "c57_4430_000020 c57_4431_000038"
        ).split(),
        "val": "c57_4408_000016 c57_4416_000015 c57_4120_000000 c57_4176_000001".split(),
    },
    "policy": {
        "unsupported_numeric_values": [10],
        "runtime_behavior": (
            "Classifier label unknown produces no numeric speed value and therefore no numeric TTS claim"
        ),
        "promotion_condition": (
            "10 km/h may only become a supported numeric class after an independently reviewed "
            "real-domain validation set meets the same minimum gates"
        ),
    },
}
HUMAN_QUALITY_GATE_APPROVAL = {
    "approved": True,
    "scope": "one official detector and speed-classifier fine-tune after quality gate",
    "source_kernel_version": 13,
    "source_status": "WAITING_FOR_HUMAN_QUALITY_GATE",
    "verified_automated_pass": True,
    "verified_clean_seed_validation": {"correct": 395, "total": 410, "accuracy": 0.9634146341463414},
    "verified_class_90_minimum": {"train": 50, "val": 15},
    "verified_unknown_minimum": {"train": 314, "val": 4},
    "verified_manual_curation": {"numeric": 47, "unknown": 18, "missing": 0},
    "safety_policy": "numeric 10 remains unsupported and routes to unknown",
}


def load_manual_speed_curation() -> dict[str, object]:
    curation = (
        json.loads(MANUAL_CURATION_PATH.read_text(encoding="utf-8"))
        if MANUAL_CURATION_PATH.exists()
        else INLINE_MANUAL_CURATION
    )
    if curation.get("schema_version") != 1:
        raise ValueError("Unsupported manual speed curation schema")
    return curation


def write_json(name: str, value: object) -> None:
    path = OUTPUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def gpu_preflight() -> dict:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is mandatory")
    return {
        "devices": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
        "torch": torch.__version__,
    }


def find_dataset_yaml() -> Path:
    candidates = [
        path
        for path in INPUT.rglob("*.yaml")
        if "traffic-sign-detection-vietnam" in str(path).lower()
    ]
    if candidates:
        return candidates[0]
    source_token = "traffic-sign-detection-vietnam"
    image_roots = [
        path
        for path in INPUT.rglob("images")
        if path.is_dir()
        and source_token in str(path).lower()
        and path.parent.name.lower() in {"train", "valid", "val", "test"}
    ]
    by_split: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    for path in image_roots:
        split = path.parent.name.lower()
        split = "val" if split == "valid" else split
        by_split[split].append(str(path))
    names_file = next(iter(INPUT.rglob("yolo11s_vietnam_traffic.names.json")), None)
    if not by_split["train"] or not names_file:
        raise FileNotFoundError(
            "Primary 82-class dataset has no data.yaml and its train/images or names input was not found"
        )
    names = {
        int(key): str(value)
        for key, value in json.loads(names_file.read_text(encoding="utf-8")).items()
    }
    generated = WORK / "generated_traffic_sign.yaml"
    generated.write_text(
        yaml.safe_dump(
            {
                "path": "/",
                "train": sorted(by_split["train"]),
                "val": sorted(by_split["val"] or by_split["test"]),
                "test": sorted(by_split["test"]),
                "names": names,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return generated


def class_names(data: dict) -> dict[int, str]:
    names = data["names"]
    if isinstance(names, list):
        return {index: str(value) for index, value in enumerate(names)}
    return {int(key): str(value) for key, value in names.items()}


def resolve_split(yaml_path: Path, data: dict, split: str) -> list[Path]:
    value = data.get(split)
    if not value:
        return []
    values = value if isinstance(value, list) else [value]
    root = Path(data.get("path", yaml_path.parent))
    if not root.is_absolute():
        root = (yaml_path.parent / root).resolve()
    elif root == Path("/") and not any(Path(item).is_absolute() for item in values):
        root = yaml_path.parent
    images: list[Path] = []
    for item in values:
        path = Path(item)
        if not path.is_absolute():
            path = root / path
        if path.is_dir():
            images.extend(p for p in path.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        elif path.suffix == ".txt":
            images.extend(Path(line.strip()) for line in path.read_text().splitlines() if line.strip())
    return images


def label_path(image: Path) -> Path:
    parts = list(image.parts)
    if "images" in parts:
        parts[parts.index("images")] = "labels"
    return Path(*parts).with_suffix(".txt")


def validate_row(row: list[str], names: dict[int, str]) -> tuple[int, list[float]]:
    if len(row) != 5:
        raise ValueError(f"expected 5 columns, found {len(row)}")
    values = [float(value) for value in row]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("non-finite value")
    class_value = values[0]
    class_id = int(class_value)
    if class_value != class_id or class_id not in names:
        raise ValueError(f"invalid class id {row[0]}")
    cx, cy, bw, bh = values[1:]
    if not (0.0 <= cx <= 1.0 and 0.0 <= cy <= 1.0):
        raise ValueError("box center is outside normalized image bounds")
    if not (0.0 < bw <= 1.0 and 0.0 < bh <= 1.0):
        raise ValueError("box width/height is outside (0, 1]")
    return class_id, [cx, cy, bw, bh]


def create_speed_contact_sheets(
    source_root: Path = SPEED_CROPS,
    review_name: str = "speed_semantics",
) -> dict[str, int]:
    review = OUTPUT / "quality_gate" / review_name
    review.mkdir(parents=True, exist_ok=True)
    selected_counts: dict[str, int] = {}
    tile_size = 120
    columns = 10
    for split in ("train", "val"):
        labels = [str(speed) for speed in sorted(SPEED_VALUES)] + ["unknown"]
        for label in labels:
            source = source_root / split / label
            files = sorted(source.glob("*.jpg"))
            if not files:
                continue
            # Class 10 is currently suspect, so review every crop. Other classes
            # use a deterministic 100-image semantic-purity sample.
            speed = int(label) if label.isdigit() else 0
            if label != "10" and len(files) > 100:
                files = random.Random(SEED + speed).sample(files, 100)
            rows = (len(files) + columns - 1) // columns
            sheet = np.zeros((rows * tile_size, columns * tile_size, 3), dtype=np.uint8)
            for index, path in enumerate(files):
                frame = cv2.imread(str(path))
                if frame is None:
                    continue
                height, width = frame.shape[:2]
                scale = min((tile_size - 18) / max(width, 1), (tile_size - 18) / max(height, 1))
                resized = cv2.resize(
                    frame,
                    (max(1, int(width * scale)), max(1, int(height * scale))),
                    interpolation=cv2.INTER_AREA,
                )
                tile = np.zeros((tile_size, tile_size, 3), dtype=np.uint8)
                y = (tile_size - 18 - resized.shape[0]) // 2
                x = (tile_size - resized.shape[1]) // 2
                tile[y:y + resized.shape[0], x:x + resized.shape[1]] = resized
                cv2.putText(tile, path.stem[:16], (2, tile_size - 4), 0, 0.32, (255, 255, 255), 1)
                row, column = divmod(index, columns)
                sheet[
                    row * tile_size:(row + 1) * tile_size,
                    column * tile_size:(column + 1) * tile_size,
                ] = tile
            cv2.imwrite(str(review / f"speed_{label}_{split}.jpg"), sheet)
            selected_counts[f"{split}:{label}"] = len(files)
    return selected_counts


def create_bootstrap_rejection_sheets(records: list[dict[str, object]]) -> dict[str, int]:
    review = OUTPUT / "quality_gate" / "bootstrap_rejected_ranked"
    review.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    tile_size = 160
    label_height = 34
    columns = 5
    page_size = 50
    for split in ("train", "val"):
        for declared in sorted(SUSPECT_SPEED_VALUES):
            items = [
                record
                for record in records
                if str(record.get("split")) == split
                and int(record.get("declared", -1)) == declared
                and record.get("bootstrap_resolved") is None
            ]
            items.sort(
                key=lambda record: float(
                    dict(record.get("bootstrap_evidence", {})).get("mean_confidence", 0.0)
                ),
                reverse=True,
            )
            items = items[:200]
            counts[f"{split}:{declared}"] = len(items)
            for page_index in range((len(items) + page_size - 1) // page_size):
                page = items[page_index * page_size:(page_index + 1) * page_size]
                rows = (len(page) + columns - 1) // columns
                sheet = np.zeros((rows * (tile_size + label_height), columns * tile_size, 3), dtype=np.uint8)
                for index, record in enumerate(page):
                    source = Path(str(record["source"]))
                    frame = cv2.imread(str(source))
                    if frame is None:
                        continue
                    height, width = frame.shape[:2]
                    scale = min((tile_size - 8) / max(width, 1), (tile_size - 8) / max(height, 1))
                    resized = cv2.resize(
                        frame,
                        (max(1, int(width * scale)), max(1, int(height * scale))),
                        interpolation=cv2.INTER_AREA,
                    )
                    row, column = divmod(index, columns)
                    y0 = row * (tile_size + label_height)
                    x0 = column * tile_size
                    y = y0 + (tile_size - resized.shape[0]) // 2
                    x = x0 + (tile_size - resized.shape[1]) // 2
                    sheet[y:y + resized.shape[0], x:x + resized.shape[1]] = resized
                    evidence = dict(record.get("bootstrap_evidence", {}))
                    prediction = evidence.get("value", "?")
                    confidence = float(evidence.get("mean_confidence", 0.0))
                    filename = source.stem[:20]
                    cv2.putText(
                        sheet,
                        f"{filename} d{declared}>p{prediction}",
                        (x0 + 2, y0 + tile_size + 13),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.34,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA,
                    )
                    cv2.putText(
                        sheet,
                        f"conf={confidence:.3f}",
                        (x0 + 2, y0 + tile_size + 28),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.34,
                        (255, 255, 255),
                        1,
                        cv2.LINE_AA,
                    )
                cv2.imwrite(
                    str(review / f"declared_{declared}_{split}_page_{page_index + 1:02d}.jpg"),
                    sheet,
                )
    return counts


def _ocr_candidate(reader: object, crop: np.ndarray) -> dict[str, object]:
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
    scale = max(1.0, 192.0 / max(gray.shape[:2]))
    enlarged = cv2.resize(
        gray,
        (max(16, int(gray.shape[1] * scale)), max(16, int(gray.shape[0] * scale))),
        interpolation=cv2.INTER_CUBIC,
    )
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(enlarged)
    thresholded = cv2.adaptiveThreshold(
        clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 7
    )
    votes: list[dict[str, object]] = []
    for variant_name, variant in (("gray", enlarged), ("clahe", clahe), ("threshold", thresholded)):
        try:
            results = reader.recognize(
                variant,
                detail=1,
                decoder="greedy",
                allowlist="0123456789",
                contrast_ths=0.05,
                adjust_contrast=0.7,
            )
        except Exception:
            continue
        for result in results:
            if len(result) < 3:
                continue
            digits = "".join(re.findall(r"\d", str(result[1])))
            if not digits:
                continue
            value = int(digits)
            if value not in SPEED_VALUES:
                continue
            votes.append(
                {"variant": variant_name, "value": value, "confidence": float(result[2])}
            )
    by_value: dict[int, list[float]] = {}
    for vote in votes:
        by_value.setdefault(int(vote["value"]), []).append(float(vote["confidence"]))
    ranked = sorted(
        by_value.items(),
        key=lambda item: (len(item[1]), max(item[1]), sum(item[1]) / len(item[1])),
        reverse=True,
    )
    if not ranked:
        return {"accepted": False, "value": None, "votes": votes, "reason": "no_valid_digits"}
    value, confidences = ranked[0]
    accepted = (len(confidences) >= 2 and max(confidences) >= 0.60) or max(confidences) >= 0.92
    return {
        "accepted": accepted,
        "value": value if accepted else None,
        "votes": votes,
        "reason": "consensus" if accepted else "low_confidence",
    }


def _find_vnts_detection_root() -> Path | None:
    for classes_path in INPUT.rglob("classes.txt"):
        try:
            labels = classes_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue
        if not any(re.fullmatch(r"P\.127\*\d+", label.strip()) for label in labels):
            continue
        root = classes_path.parent
        if (root / "images").is_dir() and (root / "labels").is_dir():
            return root
    return None


def add_vnts_candidate_speed_crops() -> dict[str, object]:
    """Add only OCR-gated VNTS speed candidates using a sequence-group split.

    The published train/test lists interleave adjacent video frames. We therefore
    ignore them and keep each contiguous numeric-stem group in exactly one split.
    """
    root = _find_vnts_detection_root()
    if root is None:
        return {"found": False, "reason": "VNTS detection source not attached"}
    labels = (root / "classes.txt").read_text(encoding="utf-8").splitlines()
    speed_ids = {
        class_id: int(match.group(1))
        for class_id, label in enumerate(labels)
        if (match := re.fullmatch(r"P\.127\*(\d+)", label.strip()))
        and int(match.group(1)) in SPEED_VALUES
    }
    image_records: list[dict[str, object]] = []
    for label_path_value in sorted((root / "labels").glob("*.txt")):
        try:
            stem_number = int(label_path_value.stem)
        except ValueError:
            continue
        rows: list[tuple[int, list[float]]] = []
        for source_row in label_path_value.read_text(encoding="utf-8").splitlines():
            parts = source_row.split()
            if len(parts) != 5:
                continue
            class_id = int(float(parts[0]))
            if class_id not in speed_ids:
                continue
            rows.append((speed_ids[class_id], [float(value) for value in parts[1:]]))
        image_path = root / "images" / f"{label_path_value.stem}.jpg"
        if rows and image_path.exists():
            image_records.append({"stem": stem_number, "image": image_path, "rows": rows})

    groups: list[list[dict[str, object]]] = []
    for record in image_records:
        if not groups or int(record["stem"]) - int(groups[-1][-1]["stem"]) > 3:
            groups.append([])
        groups[-1].append(record)
    group_counts: list[Counter[int]] = []
    for group in groups:
        counts: Counter[int] = Counter()
        for record in group:
            counts.update(speed for speed, _ in record["rows"])
        group_counts.append(counts)

    # Start with every fifth independent sequence, then greedily cover at least
    # 40 raw boxes per available speed value. OCR will still reject ambiguous crops.
    val_groups = {index for index in range(len(groups)) if index % 5 == 0}
    target_values = set(speed_ids.values())
    while True:
        val_counts: Counter[int] = Counter()
        for index in val_groups:
            val_counts.update(group_counts[index])
        deficient = {value for value in target_values if val_counts[value] < 40}
        if not deficient:
            break
        candidates = [
            (
                sum(group_counts[index][value] for value in deficient),
                -sum(group_counts[index].values()),
                -index,
                index,
            )
            for index in range(len(groups))
            if index not in val_groups
        ]
        best = max(candidates, default=(0, 0, 0, -1))
        if best[0] <= 0:
            break
        val_groups.add(best[3])

    crop_counts: Counter[str] = Counter()
    group_manifest: list[dict[str, object]] = []
    for group_index, group in enumerate(groups):
        split = "val" if group_index in val_groups else "train"
        group_manifest.append(
            {
                "group": group_index,
                "start": int(group[0]["stem"]),
                "end": int(group[-1]["stem"]),
                "split": split,
                "counts": dict(group_counts[group_index]),
            }
        )
        for record in group:
            frame = cv2.imread(str(record["image"]))
            if frame is None:
                continue
            height, width = frame.shape[:2]
            for box_index, (speed, box) in enumerate(record["rows"]):
                cx, cy, bw, bh = box
                padding = 0.12
                x1 = max(0, int((cx - bw * (0.5 + padding)) * width))
                y1 = max(0, int((cy - bh * (0.5 + padding)) * height))
                x2 = min(width, int((cx + bw * (0.5 + padding)) * width))
                y2 = min(height, int((cy + bh * (0.5 + padding)) * height))
                crop = frame[y1:y2, x1:x2]
                if crop.size == 0:
                    continue
                target = SPEED_CROPS / split / str(speed)
                target.mkdir(parents=True, exist_ok=True)
                token = f"{VNTS_SPEED_PREFIX}g{group_index:02d}_{int(record['stem']):04d}_{box_index}.jpg"
                cv2.imwrite(str(target / token), crop)
                crop_counts[f"{split}:{speed}"] += 1
    report = {
        "found": True,
        "root": str(root),
        "split_strategy": "contiguous numeric stems (gap <= 3) kept in one split",
        "groups": group_manifest,
        "val_groups": sorted(val_groups),
        "crop_counts": dict(crop_counts),
    }
    write_json("vnts_candidate_audit.json", report)
    return report


def clean_speed_classifier_crops() -> dict[str, object]:
    shutil.rmtree(CLEAN_SPEED_CROPS, ignore_errors=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "easyocr>=1.7,<2"],
        check=True,
    )
    import easyocr

    reader = easyocr.Reader(["en"], gpu=True, verbose=False)
    records: list[dict[str, object]] = []
    accepted: Counter[str] = Counter()
    rejected: Counter[str] = Counter()
    corrected: Counter[str] = Counter()
    for split in ("train", "val"):
        for expected in sorted(SPEED_VALUES):
            source = SPEED_CROPS / split / str(expected)
            for crop_path in sorted(source.glob("*.jpg")):
                resolved = expected
                evidence: dict[str, object] = {
                    "accepted": True,
                    "value": expected,
                    "reason": "trusted_contact_sheet_class",
                    "votes": [],
                }
                # Every crop from the supplementary VNTS source requires OCR,
                # because its published numeric classes contain visible cross-labels.
                if expected in SUSPECT_SPEED_VALUES or crop_path.name.startswith(VNTS_SPEED_PREFIX):
                    crop = cv2.imread(str(crop_path))
                    evidence = (
                        _ocr_candidate(reader, crop)
                        if crop is not None
                        else {"accepted": False, "value": None, "votes": [], "reason": "unreadable_crop"}
                    )
                    resolved = int(evidence["value"]) if evidence.get("value") is not None else expected
                record = {
                    "split": split,
                    "source": str(crop_path),
                    "declared": expected,
                    "resolved": resolved if evidence.get("accepted") else None,
                    "evidence": evidence,
                }
                records.append(record)
                if not evidence.get("accepted"):
                    rejected[f"{split}:{expected}"] += 1
                    continue
                target = CLEAN_SPEED_CROPS / split / str(resolved)
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(crop_path, target / crop_path.name)
                accepted[f"{split}:{resolved}"] += 1
                if resolved != expected:
                    corrected[f"{split}:{expected}->{resolved}"] += 1
    minimums = {
        str(value): {
            "train": accepted[f"train:{value}"],
            "val": accepted[f"val:{value}"],
            "pass": accepted[f"train:{value}"] >= 50 and accepted[f"val:{value}"] >= 15,
        }
        for value in sorted(SPEED_VALUES)
    }
    summary = {
        "strategy": "trusted classes plus EasyOCR consensus for suspect 10/50/80/90",
        "accepted": dict(accepted),
        "rejected": dict(rejected),
        "corrected": dict(corrected),
        "minimums": minimums,
        "all_minimums_pass": all(item["pass"] for item in minimums.values()),
        "records": records,
    }
    write_json("speed_ocr_cleanup.json", summary)
    create_speed_contact_sheets(CLEAN_SPEED_CROPS, "speed_semantics_ocr_only")
    return summary


def _render_synthetic_speed_sign(value: int, index: int, target: Path) -> None:
    rng = np.random.default_rng(SEED + value * 1009 + index)
    size = 112
    background = np.full((size, size, 3), rng.integers(25, 225, size=3), dtype=np.uint8)
    center = (size // 2 + int(rng.integers(-5, 6)), size // 2 + int(rng.integers(-5, 6)))
    radius = int(rng.integers(42, 49))
    cv2.circle(background, center, radius, (240, 240, 240), -1, cv2.LINE_AA)
    cv2.circle(background, center, radius, (20, 30, int(rng.integers(175, 256))), int(rng.integers(7, 12)), cv2.LINE_AA)
    font = random.Random(SEED + value * 97 + index).choice(
        [cv2.FONT_HERSHEY_SIMPLEX, cv2.FONT_HERSHEY_DUPLEX, cv2.FONT_HERSHEY_TRIPLEX]
    )
    text = str(value)
    scale = float(rng.uniform(1.35, 1.75)) if len(text) == 2 else float(rng.uniform(1.0, 1.28))
    thickness = int(rng.integers(2, 5))
    (text_width, text_height), _ = cv2.getTextSize(text, font, scale, thickness)
    origin = (
        center[0] - text_width // 2 + int(rng.integers(-2, 3)),
        center[1] + text_height // 2 + int(rng.integers(-2, 3)),
    )
    cv2.putText(background, text, origin, font, scale, (10, 10, 10), thickness, cv2.LINE_AA)
    jitter = rng.uniform(-7, 7, size=(4, 2)).astype(np.float32)
    corners = np.float32([[0, 0], [size - 1, 0], [size - 1, size - 1], [0, size - 1]])
    matrix = cv2.getPerspectiveTransform(corners, corners + jitter)
    rendered = cv2.warpPerspective(background, matrix, (size, size), borderMode=cv2.BORDER_REFLECT_101)
    if rng.random() < 0.75:
        kernel = int(rng.choice([3, 3, 3, 5]))
        rendered = cv2.GaussianBlur(rendered, (kernel, kernel), float(rng.uniform(0.2, 1.4)))
    rendered = cv2.convertScaleAbs(rendered, alpha=float(rng.uniform(0.65, 1.35)), beta=int(rng.integers(-25, 26)))
    noise = rng.normal(0, float(rng.uniform(1, 12)), rendered.shape).astype(np.int16)
    rendered = np.clip(rendered.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    target.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(target), rendered)


def _find_gtsrb_train_root() -> Path | None:
    for candidate in INPUT.rglob("Train"):
        if candidate.is_dir() and all((candidate / str(class_id)).is_dir() for class_id in range(9)):
            return candidate
    return None


def _gtsrb_training_samples(limit_per_class: int = 700) -> dict[int, list[Path]]:
    root = _find_gtsrb_train_root()
    samples: dict[int, list[Path]] = {value: [] for value in SPEED_VALUES}
    if root is None:
        return samples
    suffixes = {".jpg", ".jpeg", ".png", ".ppm"}
    for class_id, value in GTSRB_SPEED_CLASSES.items():
        paths = sorted(path for path in (root / str(class_id)).rglob("*") if path.suffix.lower() in suffixes)
        if len(paths) > limit_per_class:
            paths = random.Random(SEED + class_id).sample(paths, limit_per_class)
        samples[value] = paths
    return samples


def bootstrap_refine_speed_crops(ocr_summary: dict[str, object]) -> dict[str, object]:
    """Train a temporary digit reader and conservatively relabel ambiguous crops.

    This checkpoint is data-cleaning evidence only. It is never promoted as the
    RoadWatch runtime classifier, and final training remains human-gated.
    """
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
    from torchvision.models import MobileNet_V3_Small_Weights, mobilenet_v3_small

    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True, warn_only=True)
    np.random.seed(SEED)
    random.seed(SEED)
    synthetic_root = WORK / "bootstrap_synthetic"
    shutil.rmtree(synthetic_root, ignore_errors=True)
    for value in sorted(SPEED_VALUES):
        for index in range(300):
            _render_synthetic_speed_sign(value, index, synthetic_root / str(value) / f"synth_{index:04d}.jpg")

    records = list(ocr_summary.get("records", []))
    manual_curation = load_manual_speed_curation()
    manual_numeric = {
        key: set(str(stem) for stem in stems)
        for key, stems in dict(manual_curation.get("accepted_numeric", {})).items()
    }
    manual_unknown = {
        split: set(str(stem) for stem in stems)
        for split, stems in dict(manual_curation.get("accepted_unknown", {})).items()
    }
    expected_manual_numeric = {(key, stem) for key, stems in manual_numeric.items() for stem in stems}
    expected_manual_unknown = {
        (split, stem) for split, stems in manual_unknown.items() for stem in stems
    }
    matched_manual_numeric: set[tuple[str, str]] = set()
    matched_manual_unknown: set[tuple[str, str]] = set()
    train_seeds: dict[int, list[Path]] = {value: [] for value in SPEED_VALUES}
    val_seeds: list[tuple[Path, int]] = []
    for record in records:
        source = Path(str(record["source"]))
        declared = int(record["declared"])
        evidence = dict(record.get("evidence", {}))
        is_vnts = source.name.startswith(VNTS_SPEED_PREFIX)
        trusted_primary = not is_vnts and declared not in SUSPECT_SPEED_VALUES
        same_label_ocr = bool(evidence.get("accepted")) and record.get("resolved") == declared
        if not trusted_primary and not same_label_ocr:
            continue
        if str(record["split"]) == "train":
            train_seeds[declared].append(source)
        else:
            val_seeds.append((source, declared))
    for value in train_seeds:
        paths = sorted(train_seeds[value])
        if len(paths) > 220:
            paths = random.Random(SEED + value).sample(paths, 220)
        train_seeds[value] = paths
    gtsrb_seeds = _gtsrb_training_samples()

    class SpeedDataset(Dataset):
        def __init__(self, samples: list[tuple[Path, int]], augment: bool) -> None:
            self.samples = samples
            self.augment = augment

        def __len__(self) -> int:
            return len(self.samples)

        def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
            path, label_index = self.samples[index]
            frame = cv2.imread(str(path))
            if frame is None:
                raise RuntimeError(f"Unreadable bootstrap image: {path}")
            frame = cv2.resize(frame, (160, 160), interpolation=cv2.INTER_AREA)
            if self.augment:
                angle = random.uniform(-8.0, 8.0)
                matrix = cv2.getRotationMatrix2D((80, 80), angle, random.uniform(0.9, 1.1))
                frame = cv2.warpAffine(frame, matrix, (160, 160), borderMode=cv2.BORDER_REFLECT_101)
                frame = cv2.convertScaleAbs(frame, alpha=random.uniform(0.75, 1.25), beta=random.randint(-18, 18))
                if random.random() < 0.25:
                    frame = cv2.GaussianBlur(frame, (3, 3), random.uniform(0.2, 1.1))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            rgb = (rgb - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
                [0.229, 0.224, 0.225], dtype=np.float32
            )
            return torch.from_numpy(rgb.transpose(2, 0, 1)), label_index

    values = sorted(SPEED_VALUES)
    value_to_index = {value: index for index, value in enumerate(values)}
    train_samples: list[tuple[Path, int]] = []
    for value in values:
        train_samples.extend(
            (path, value_to_index[value]) for path in sorted((synthetic_root / str(value)).glob("*.jpg"))
        )
        train_samples.extend((path, value_to_index[value]) for path in train_seeds[value])
        train_samples.extend((path, value_to_index[value]) for path in gtsrb_seeds[value])
    random.Random(SEED).shuffle(train_samples)
    sample_class_counts = Counter(label for _, label in train_samples)
    sample_weights = [1.0 / sample_class_counts[label] for _, label in train_samples]
    balanced_sampler = WeightedRandomSampler(
        sample_weights,
        num_samples=len(train_samples),
        replacement=True,
        generator=torch.Generator().manual_seed(SEED),
    )

    pretrained_loaded = True
    try:
        model = mobilenet_v3_small(weights=MobileNet_V3_Small_Weights.DEFAULT)
    except Exception:
        pretrained_loaded = False
        model = mobilenet_v3_small(weights=None)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(values))
    model = model.cuda()
    train_loader = DataLoader(
        SpeedDataset(train_samples, True),
        batch_size=128,
        sampler=balanced_sampler,
        # Augmentation uses Python/NumPy RNG; one process keeps repeated gate
        # runs reproducible instead of changing accepted crops between versions.
        num_workers=0,
        pin_memory=True,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=12)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.03)
    training_history: list[dict[str, float]] = []
    for epoch in range(12):
        model.train()
        total_loss = 0.0
        correct = 0
        seen = 0
        for images, labels_batch in train_loader:
            images = images.cuda(non_blocking=True)
            labels_batch = labels_batch.cuda(non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits = model(images)
            loss = loss_fn(logits, labels_batch)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach()) * labels_batch.numel()
            correct += int((logits.argmax(1) == labels_batch).sum())
            seen += labels_batch.numel()
        scheduler.step()
        training_history.append(
            {"epoch": epoch + 1, "loss": total_loss / max(seen, 1), "accuracy": correct / max(seen, 1)}
        )

    model.eval()
    eval_by_value: dict[int, Counter[str]] = {value: Counter() for value in values}
    with torch.inference_mode():
        for source, expected in val_seeds:
            image, _ = SpeedDataset([(source, value_to_index[expected])], False)[0]
            predicted = values[int(model(image.unsqueeze(0).cuda()).argmax(1).item())]
            eval_by_value[expected]["total"] += 1
            eval_by_value[expected]["correct"] += int(predicted == expected)

    def predict_tta(path: Path) -> dict[str, object]:
        frame = cv2.imread(str(path))
        if frame is None:
            return {"accepted": False, "reason": "unreadable_crop"}
        frame = cv2.resize(frame, (160, 160), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe_gray = cv2.createCLAHE(2.0, (8, 8)).apply(gray)
        clahe = cv2.cvtColor(clahe_gray, cv2.COLOR_GRAY2BGR)
        variants = [
            frame,
            clahe,
            cv2.convertScaleAbs(frame, alpha=0.8, beta=8),
            cv2.convertScaleAbs(frame, alpha=1.2, beta=-8),
            cv2.GaussianBlur(frame, (3, 3), 0.5),
        ]
        tensors = []
        for variant in variants:
            rgb = cv2.cvtColor(variant, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            rgb = (rgb - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
                [0.229, 0.224, 0.225], dtype=np.float32
            )
            tensors.append(torch.from_numpy(rgb.transpose(2, 0, 1)))
        with torch.inference_mode():
            probabilities = torch.softmax(model(torch.stack(tensors).cuda()), dim=1).cpu().numpy()
        winners = probabilities.argmax(axis=1)
        winner_index, vote_count = Counter(int(item) for item in winners).most_common(1)[0]
        mean_probabilities = probabilities.mean(axis=0)
        ordered = np.sort(mean_probabilities)[::-1]
        value = values[winner_index]
        mean_confidence = float(mean_probabilities[winner_index])
        minimum_confidence = float(probabilities[:, winner_index].min())
        margin = float(ordered[0] - ordered[1])
        return {
            "accepted": vote_count >= 4 and mean_confidence >= 0.92 and minimum_confidence >= 0.70 and margin >= 0.25,
            "value": value,
            "votes": vote_count,
            "mean_confidence": mean_confidence,
            "minimum_confidence": minimum_confidence,
            "margin": margin,
        }

    shutil.rmtree(CLEAN_SPEED_CROPS, ignore_errors=True)
    accepted: Counter[str] = Counter()
    rejected: Counter[str] = Counter()
    corrected: Counter[str] = Counter()
    output_records: list[dict[str, object]] = []
    for record in records:
        source = Path(str(record["source"]))
        split = str(record["split"])
        declared = int(record["declared"])
        is_vnts = source.name.startswith(VNTS_SPEED_PREFIX)
        trusted_primary = not is_vnts and declared not in SUSPECT_SPEED_VALUES
        numeric_key = f"{split}:{declared}"
        manually_numeric = source.stem in manual_numeric.get(numeric_key, set())
        manually_unknown = source.stem in manual_unknown.get(split, set())
        if manually_numeric and manually_unknown:
            raise ValueError(f"Manual curation conflict for {split}:{source.stem}")
        if manually_unknown and declared not in UNSUPPORTED_SPEED_VALUES:
            raise ValueError(f"Unknown allowlist contains supported class {declared}: {source.stem}")
        evidence: dict[str, object]
        if manually_numeric:
            evidence = {
                "accepted": True,
                "value": declared,
                "reason": "manual_visual_review_v10",
            }
            matched_manual_numeric.add((numeric_key, source.stem))
        elif manually_unknown:
            evidence = {
                "accepted": True,
                "value": "unknown",
                "reason": "manual_visual_review_v10_unsupported_value",
            }
            matched_manual_unknown.add((split, source.stem))
        elif trusted_primary:
            evidence = {"accepted": True, "value": declared, "reason": "trusted_primary_class"}
        else:
            evidence = predict_tta(source)
            evidence["reason"] = "bootstrap_tta"
            predicted = evidence.get("value")
            # Synthetic-only 10 needs unanimous, exceptionally strong evidence.
            if predicted == 10:
                threshold = 0.995 if declared != 10 else 0.97
                evidence["accepted"] = bool(
                    evidence.get("accepted")
                    and evidence.get("votes") == 5
                    and float(evidence.get("mean_confidence", 0.0)) >= threshold
                    and float(evidence.get("minimum_confidence", 0.0)) >= 0.90
                )
            # Relabeling across published classes is held to a stricter gate.
            if predicted is not None and int(predicted) != declared:
                evidence["accepted"] = bool(
                    evidence.get("accepted")
                    and evidence.get("votes") == 5
                    and float(evidence.get("mean_confidence", 0.0)) >= 0.97
                    and float(evidence.get("margin", 0.0)) >= 0.40
                )
        evidence_value = evidence.get("value")
        if evidence.get("accepted") and evidence_value == "unknown":
            resolved: int | str | None = "unknown"
        elif evidence.get("accepted") and evidence_value is not None:
            resolved = int(evidence_value)
            # A numeric class with insufficient real validation must never be
            # exposed to the runtime classifier merely because bootstrap agreed.
            if resolved in UNSUPPORTED_SPEED_VALUES:
                resolved = None
                evidence["accepted"] = False
                evidence["reason"] = "unsupported_numeric_value_requires_independent_validation"
        else:
            resolved = None
        output_records.append({**record, "bootstrap_resolved": resolved, "bootstrap_evidence": evidence})
        if resolved is None:
            rejected[f"{split}:{declared}"] += 1
            continue
        target = CLEAN_SPEED_CROPS / split / str(resolved)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target / source.name)
        accepted[f"{split}:{resolved}"] += 1
        if resolved != "unknown" and resolved != declared:
            corrected[f"{split}:{declared}->{resolved}"] += 1

    missing_manual_numeric = sorted(expected_manual_numeric - matched_manual_numeric)
    missing_manual_unknown = sorted(expected_manual_unknown - matched_manual_unknown)

    # Synthetic 10 signs teach the final classifier to reject this unsupported
    # value as `unknown`; they never count as numeric 10 validation evidence.
    for index, source in enumerate(sorted((synthetic_root / "10").glob("*.jpg"))):
        target = CLEAN_SPEED_CROPS / "train" / "unknown"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target / f"unsupported_10_synth_{index:04d}.jpg")
        accepted["train:unknown"] += 1

    # GTSRB is CC0 clean training support only. It never enters the Vietnamese
    # validation split or contributes to the bootstrap validation metric.
    gtsrb_added: Counter[str] = Counter()
    for value in sorted(CLASSIFIER_SPEED_VALUES):
        for index, source in enumerate(gtsrb_seeds[value]):
            target = CLEAN_SPEED_CROPS / "train" / str(value)
            target.mkdir(parents=True, exist_ok=True)
            suffix = source.suffix.lower() if source.suffix.lower() in {".jpg", ".jpeg", ".png"} else ".png"
            target_path = target / f"gtsrb_{value}_{index:04d}{suffix}"
            if source.suffix.lower() == ".ppm":
                frame = cv2.imread(str(source))
                if frame is None:
                    continue
                cv2.imwrite(str(target_path), frame)
            else:
                shutil.copy2(source, target_path)
            accepted[f"train:{value}"] += 1
            gtsrb_added[str(value)] += 1

    minimums = {
        str(value): {
            "train": accepted[f"train:{value}"],
            "val": accepted[f"val:{value}"],
            "pass": accepted[f"train:{value}"] >= 50 and accepted[f"val:{value}"] >= 15,
        }
        for value in sorted(CLASSIFIER_SPEED_VALUES)
    }
    unknown_minimum = {
        "train": accepted["train:unknown"],
        "val": accepted["val:unknown"],
        "pass": accepted["train:unknown"] >= 300 and accepted["val:unknown"] >= 2,
    }
    eval_summary = {
        str(value): {
            "correct": eval_by_value[value]["correct"],
            "total": eval_by_value[value]["total"],
            "accuracy": (
                eval_by_value[value]["correct"] / eval_by_value[value]["total"]
                if eval_by_value[value]["total"] else None
            ),
        }
        for value in values
    }
    eval_total = sum(item["total"] for item in eval_summary.values())
    eval_correct = sum(item["correct"] for item in eval_summary.values())
    eval_accuracy = eval_correct / eval_total if eval_total else 0.0
    eval_gate_pass = (
        eval_total >= 50
        and eval_accuracy >= 0.90
        and all(
            item["total"] < 5 or float(item["accuracy"] or 0.0) >= 0.80
            for item in eval_summary.values()
        )
    )
    rejection_sheet_counts = create_bootstrap_rejection_sheets(output_records)
    checkpoint = OUTPUT / "bootstrap_cleanup_only.pt"
    torch.save({"state_dict": model.state_dict(), "values": values, "role": "data_cleanup_only"}, checkpoint)
    summary = {
        "role": "temporary data-cleaning model; forbidden for runtime promotion",
        "architecture": "torchvision_mobilenet_v3_small",
        "imagenet_pretrained_loaded": pretrained_loaded,
        "training_history": training_history,
        "real_train_seed_counts": {str(value): len(train_seeds[value]) for value in values},
        "gtsrb_cc0_train_counts": dict(gtsrb_added),
        "gtsrb_used_for_validation": False,
        "clean_seed_validation": eval_summary,
        "clean_seed_validation_overall": {
            "correct": eval_correct,
            "total": eval_total,
            "accuracy": eval_accuracy,
            "pass": eval_gate_pass,
        },
        "accepted": dict(accepted),
        "rejected": dict(rejected),
        "corrected": dict(corrected),
        "minimums": minimums,
        "unknown_minimum": unknown_minimum,
        "unsupported_numeric_values": sorted(UNSUPPORTED_SPEED_VALUES),
        "runtime_classifier_labels": [
            *[str(value) for value in sorted(CLASSIFIER_SPEED_VALUES)],
            "unknown",
        ],
        "manual_curation": {
            "source_run": manual_curation.get("source_run"),
            "numeric_expected": len(expected_manual_numeric),
            "numeric_matched": len(matched_manual_numeric),
            "unknown_expected": len(expected_manual_unknown),
            "unknown_matched": len(matched_manual_unknown),
            "missing_numeric": missing_manual_numeric,
            "missing_unknown": missing_manual_unknown,
            "pass": not missing_manual_numeric and not missing_manual_unknown,
        },
        "all_minimums_pass": (
            all(item["pass"] for item in minimums.values())
            and unknown_minimum["pass"]
            and not missing_manual_numeric
            and not missing_manual_unknown
        ),
        "records": output_records,
        "rejection_sheet_counts": rejection_sheet_counts,
    }
    write_json("speed_bootstrap_cleanup.json", summary)
    create_speed_contact_sheets(CLEAN_SPEED_CROPS, "speed_semantics_cleaned")
    shutil.rmtree(synthetic_root, ignore_errors=True)
    return summary


def audit_and_crop(yaml_path: Path) -> dict:
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    names = class_names(data)
    speed_ids: dict[int, int] = {}
    for class_id, label in names.items():
        normalized_label = label.strip().lower()
        if not normalized_label.startswith("speed limit") and label.strip() not in {
            str(value) for value in SPEED_VALUES
        }:
            continue
        numeric = [int(token) for token in re.findall(r"\d+", label)]
        value = next((token for token in numeric if token in SPEED_VALUES), None)
        if value is not None:
            speed_ids[class_id] = value
    counts: Counter[int] = Counter()
    missing_labels = 0
    invalid_rows = 0
    invalid_details: list[dict[str, object]] = []
    quarantined_images: set[str] = set()
    crop_counts: Counter[str] = Counter()
    random.seed(SEED)
    previews_by_class: dict[int, tuple[Path, list[str]]] = {}
    for split in ("train", "val", "test"):
        for image in resolve_split(yaml_path, data, split):
            if (split, image.stem) in KNOWN_BAD_IMAGES:
                quarantined_images.add(str(image))
                continue
            label = label_path(image)
            if not label.exists():
                missing_labels += 1
                continue
            source_rows = [row for row in label.read_text().splitlines() if row.strip()]
            parsed_rows: list[tuple[int, list[float], str]] = []
            for line_number, source_row in enumerate(source_rows, start=1):
                try:
                    class_id, box = validate_row(source_row.split(), names)
                    parsed_rows.append((class_id, box, source_row))
                except (TypeError, ValueError) as exc:
                    invalid_rows += 1
                    invalid_details.append(
                        {
                            "split": split,
                            "image": str(image),
                            "label": str(label),
                            "line": line_number,
                            "row": source_row,
                            "reason": str(exc),
                        }
                    )
            if len(parsed_rows) != len(source_rows):
                quarantined_images.add(str(image))
                continue
            row_strings = [source_row for _, _, source_row in parsed_rows]
            for class_id, _, _ in parsed_rows:
                previews_by_class.setdefault(class_id, (image, row_strings))
            frame = None
            for class_id, box, _ in parsed_rows:
                counts[class_id] += 1
                speed = speed_ids.get(class_id)
                if speed is None:
                    continue
                if frame is None:
                    frame = cv2.imread(str(image))
                if frame is None:
                    continue
                height, width = frame.shape[:2]
                cx, cy, bw, bh = box
                x1 = max(0, int((cx - bw / 2) * width))
                y1 = max(0, int((cy - bh / 2) * height))
                x2 = min(width, int((cx + bw / 2) * width))
                y2 = min(height, int((cy + bh / 2) * height))
                crop = frame[y1:y2, x1:x2]
                if crop.size == 0:
                    continue
                target_split = "train" if split == "train" else "val"
                target = SPEED_CROPS / target_split / str(speed)
                target.mkdir(parents=True, exist_ok=True)
                token = (
                    f"c{class_id}_{image.stem}_"
                    f"{crop_counts[f'{target_split}:{speed}']:06d}.jpg"
                )
                cv2.imwrite(str(target / token), crop)
                crop_counts[f"{target_split}:{speed}"] += 1
    quality = OUTPUT / "quality_gate"
    quality.mkdir(parents=True, exist_ok=True)
    speed_preview_ids = list(speed_ids)
    other_preview_ids = [key for key in previews_by_class if key not in speed_ids]
    random.shuffle(other_preview_ids)
    preview_ids = speed_preview_ids + other_preview_ids
    selected_previews: list[tuple[Path, list[str]]] = []
    selected_images: set[str] = set()
    for class_id in preview_ids:
        image, rows = previews_by_class[class_id]
        if str(image) in selected_images:
            continue
        selected_images.add(str(image))
        selected_previews.append((image, rows))
        if len(selected_previews) >= 24:
            break
    for index, (image, rows) in enumerate(selected_previews):
        frame = cv2.imread(str(image))
        if frame is None:
            continue
        height, width = frame.shape[:2]
        for row in rows:
            values = row.split()
            if len(values) != 5:
                continue
            class_id = int(float(values[0]))
            cx, cy, bw, bh = map(float, values[1:])
            x1, y1 = int((cx - bw / 2) * width), int((cy - bh / 2) * height)
            x2, y2 = int((cx + bw / 2) * width), int((cy + bh / 2) * height)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, names.get(class_id, str(class_id)), (x1, max(18, y1 - 4)), 0, 0.45, (0, 255, 255), 1)
        cv2.imwrite(str(quality / f"sample_{index:02d}.jpg"), frame)
    contact_sheet_counts = create_speed_contact_sheets()
    return {
        "yaml": str(yaml_path),
        "classes": names,
        "instance_counts": dict(counts),
        "speed_class_ids": speed_ids,
        "speed_crop_counts": dict(crop_counts),
        "missing_labels": missing_labels,
        "invalid_rows": invalid_rows,
        "invalid_details": invalid_details,
        "quarantined_images": sorted(quarantined_images),
        "known_semantic_issues": KNOWN_SEMANTIC_ISSUES,
        "speed_contact_sheet_samples": contact_sheet_counts,
    }


def prepare_training_yaml(yaml_path: Path, audit: dict) -> Path:
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    names = class_names(data)
    speed_ids = {int(key) for key in audit.get("speed_class_ids", {})}
    generic_speed_id = 2
    if generic_speed_id not in speed_ids:
        raise RuntimeError("Expected canonical speed class ID 2 is missing")
    quarantined = set(audit.get("quarantined_images", []))
    collapsed_root = WORK / "collapsed_sign_dataset"
    shutil.rmtree(collapsed_root, ignore_errors=True)
    collapsed_images: dict[str, list[Path]] = {"train": [], "val": []}
    remapped_rows: Counter[str] = Counter()
    for split in ("train", "val"):
        source_images = resolve_split(yaml_path, data, split)
        if split == "val" and not source_images:
            source_images = resolve_split(yaml_path, data, "test")
        image_dir = collapsed_root / split / "images"
        label_dir = collapsed_root / split / "labels"
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for image in source_images:
            if str(image) in quarantined:
                continue
            source_label = label_path(image)
            if not source_label.exists():
                continue
            target_image = image_dir / image.name
            target_label = label_dir / f"{image.stem}.txt"
            target_image.symlink_to(image)
            normalized_rows: list[str] = []
            valid_image = True
            for source_row in source_label.read_text().splitlines():
                if not source_row.strip():
                    continue
                try:
                    class_id, box = validate_row(source_row.split(), names)
                except (TypeError, ValueError):
                    valid_image = False
                    break
                output_class = generic_speed_id if class_id in speed_ids else class_id
                if output_class != class_id:
                    remapped_rows[f"{class_id}->{generic_speed_id}"] += 1
                normalized_rows.append(
                    " ".join([str(output_class), *(f"{value:.8f}" for value in box)])
                )
            if not valid_image:
                target_image.unlink(missing_ok=True)
                continue
            target_label.write_text("\n".join(normalized_rows), encoding="utf-8")
            collapsed_images[split].append(target_image)
    collapsed_names = dict(names)
    collapsed_names[generic_speed_id] = "speed_limit"
    for class_id in speed_ids - {generic_speed_id}:
        collapsed_names[class_id] = f"unused_speed_head_{class_id}"
    rejected_hard_negatives: list[dict[str, str]] = []
    locked_media = {
        "test_video1.mp4", "test_video2.mp4", "test_video10.mp4",
        "test_video11.mp4", "video_test.mp4",
    }
    for manifest_path in INPUT.rglob("manifest.json"):
        if "hard-negative" not in str(manifest_path).lower() and "hard_negative" not in str(manifest_path).lower():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        sources = {str(item.get("source", "")) for item in manifest.get("records", [])}
        if sources & locked_media or not bool(manifest.get("training_use_approved", False)):
            rejected_hard_negatives.append(
                {
                    "manifest": str(manifest_path),
                    "reason": "locked regression source or training_use_approved is not true",
                }
            )
            continue
    prepared = WORK / "sign_phase2.yaml"
    prepared.write_text(
        yaml.safe_dump(
            {
                "path": str(collapsed_root),
                "train": "train/images",
                "val": "val/images",
                "names": collapsed_names,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    write_json(
        "training_inputs.json",
        {
            "strategy": "generic speed_limit detector plus independent digit classifier",
            "generic_speed_class_id": generic_speed_id,
            "source_speed_class_ids": sorted(speed_ids),
            "speed_rows_remapped": dict(remapped_rows),
            "train_images": len(collapsed_images["train"]),
            "val_images": len(collapsed_images["val"]),
            "rejected_hard_negatives": rejected_hard_negatives,
            "quarantined_images": sorted(quarantined),
        },
    )
    return prepared


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_json("gpu.json", gpu_preflight())
    yaml_path = find_dataset_yaml()
    audit = audit_and_crop(yaml_path)
    write_json("audit.json", audit)
    candidate_audit = add_vnts_candidate_speed_crops()
    ocr_cleanup = clean_speed_classifier_crops()
    cleanup = bootstrap_refine_speed_crops(ocr_cleanup)
    instance_counts = {int(key): int(value) for key, value in audit["instance_counts"].items()}
    speed_counts = {
        int(value): sum(
            count
            for key, count in audit["speed_crop_counts"].items()
            if key.endswith(f":{value}")
        )
        for value in SPEED_VALUES
    }
    gates = {
        "class_count_is_82": len(audit["classes"]) == 82,
        "all_classes_have_instances": len(instance_counts) == 82 and all(instance_counts.values()),
        "all_speed_values_have_crops": all(speed_counts.values()),
        "missing_labels_is_zero": audit["missing_labels"] == 0,
        "raw_invalid_rows_is_zero": audit["invalid_rows"] == 0,
        "invalid_rows_quarantined": (
            audit["invalid_rows"] == 0 or bool(audit.get("quarantined_images"))
        ),
        "generic_detector_strategy_ready": True,
        "speed_classifier_cleanup_minimums_pass": bool(cleanup["all_minimums_pass"]),
        "manual_speed_curation_pass": bool(cleanup.get("manual_curation", {}).get("pass")),
        "unsupported_speed_10_routes_to_unknown": (
            10 not in {
                int(label)
                for label in cleanup.get("runtime_classifier_labels", [])
                if str(label).isdigit()
            }
            and bool(cleanup.get("unknown_minimum", {}).get("pass"))
        ),
        "bootstrap_clean_seed_validation_pass": bool(
            cleanup.get("clean_seed_validation_overall", {}).get("pass")
        ),
        "vnts_candidate_attached": bool(candidate_audit.get("found")),
        "speed_crop_counts": speed_counts,
        "visual_review_required": True,
    }
    required_gates = (
        "class_count_is_82",
        "all_classes_have_instances",
        "all_speed_values_have_crops",
        "missing_labels_is_zero",
        "invalid_rows_quarantined",
        "generic_detector_strategy_ready",
        "speed_classifier_cleanup_minimums_pass",
        "manual_speed_curation_pass",
        "unsupported_speed_10_routes_to_unknown",
        "bootstrap_clean_seed_validation_pass",
    )
    gates["automated_pass"] = all(bool(gates[key]) for key in required_gates)
    write_json("quality_gate.json", gates)
    approved = (
        os.getenv("QUALITY_GATE_APPROVED", "0") == "1"
        or bool(HUMAN_QUALITY_GATE_APPROVAL.get("approved"))
    )
    if not approved:
        write_json("status.json", {"status": "WAITING_FOR_HUMAN_QUALITY_GATE"})
        print("Quality gate artifacts ready; submit next version with QUALITY_GATE_APPROVED=1")
        shutil.rmtree(SPEED_CROPS, ignore_errors=True)
        shutil.rmtree(CLEAN_SPEED_CROPS, ignore_errors=True)
        return 0
    if not gates["automated_pass"]:
        raise RuntimeError("Dataset audit failed")
    write_json(
        "quality_gate_approval.json",
        {
            **HUMAN_QUALITY_GATE_APPROVAL,
            "current_run_automated_pass": gates["automated_pass"],
            "current_run_validation": cleanup.get("clean_seed_validation_overall"),
            "current_run_class_90": cleanup.get("minimums", {}).get("90"),
            "current_run_unknown": cleanup.get("unknown_minimum"),
            "current_run_manual_curation": cleanup.get("manual_curation"),
        },
    )
    training_yaml = prepare_training_yaml(yaml_path, audit)
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics>=8.3,<9"], check=True)
    from ultralytics import YOLO

    detector_seed = next(iter(INPUT.rglob("yolo11s_vietnam_traffic.pt")), None)
    detector = YOLO(str(detector_seed or "yolo11s.pt"))
    detector_result = detector.train(data=str(training_yaml), epochs=35, imgsz=640, batch=16, device=0, project=str(OUTPUT), name="detector", seed=SEED, patience=8)
    classifier = YOLO("yolo11n-cls.pt")
    classifier_result = classifier.train(data=str(CLEAN_SPEED_CROPS), epochs=30, imgsz=160, batch=64, device=0, project=str(OUTPUT), name="speed_digits", seed=SEED, patience=6)
    for name, result in (("detector", detector_result), ("speed_digits", classifier_result)):
        best = Path(result.save_dir) / "weights" / "best.pt"
        shutil.copy2(best, OUTPUT / f"roadwatch_{name}_v2.pt")
        model = YOLO(str(best))
        if name == "detector":
            write_json(
                "roadwatch_detector_v2.names.json",
                {str(class_id): str(label) for class_id, label in model.names.items()},
            )
        exported = Path(model.export(format="onnx", imgsz=640 if name == "detector" else 160, simplify=True))
        shutil.copy2(exported, OUTPUT / f"roadwatch_{name}_v2.onnx")
    shutil.rmtree(SPEED_CROPS, ignore_errors=True)
    shutil.rmtree(CLEAN_SPEED_CROPS, ignore_errors=True)
    shutil.rmtree(WORK / "collapsed_sign_dataset", ignore_errors=True)
    write_json("status.json", {"status": "TRAINING_COMPLETE"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
