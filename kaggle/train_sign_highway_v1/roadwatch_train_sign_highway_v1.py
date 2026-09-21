from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import shutil
from collections import Counter
from pathlib import Path

ALLOWED = {
    "speed_limit_max", "speed_limit_min", "no_entry", "no_cars", "no_trucks",
    "no_buses", "no_motorcycles", "no_bicycles", "no_pedestrians",
    "no_vehicles", "height_limit", "width_limit", "weight_limit", "unknown_sign",
}
EPOCHS = {"pilot": 1, "smoke": 5, "full": 50}
ROOT = Path("/kaggle/input")
OUT = Path("/kaggle/working/roadwatch_sign_highway_v1")


def dump(name: str, payload: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_yaml() -> Path:
    candidates = list(ROOT.rglob("data.yaml")) + list(ROOT.rglob("dataset.yaml"))
    if len(candidates) != 1:
        raise RuntimeError(f"Expected exactly one dataset YAML, found {len(candidates)}")
    return candidates[0]


def audit_dataset(yaml_path: Path, profile: str) -> dict:
    import yaml
    cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    names = cfg.get("names", {})
    names = [names[k] for k in sorted(names, key=int)] if isinstance(names, dict) else list(names)
    unknown = sorted(set(names) - ALLOWED)
    required_by_profile = {
        "minimum_speed": {"speed_limit_max", "speed_limit_min"},
        "highway_full": {"speed_limit_max", "speed_limit_min", "no_trucks", "no_vehicles"},
    }
    if profile not in required_by_profile:
        raise ValueError(f"Unsupported DATASET_PROFILE={profile}")
    required = required_by_profile[profile]
    label_files = sorted((yaml_path.parent / "labels").rglob("*.txt"))
    counts = Counter()
    invalid = []
    for path in label_files:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            parts = line.split()
            if len(parts) != 5:
                invalid.append(f"{path}:{line_no}")
                continue
            try:
                class_id = int(parts[0])
                values = [float(x) for x in parts[1:]]
            except ValueError:
                invalid.append(f"{path}:{line_no}")
                continue
            if not 0 <= class_id < len(names):
                invalid.append(f"{path}:{line_no}")
                continue
            if any(not math.isfinite(x) or not 0.0 <= x <= 1.0 for x in values) or values[2] <= 0 or values[3] <= 0:
                invalid.append(f"{path}:{line_no}")
                continue
            counts[names[class_id]] += 1
    missing = sorted(required - set(counts))
    result = {
        "yaml": str(yaml_path), "names": names, "label_files": len(label_files),
        "instances": dict(counts), "unknown_classes": unknown, "dataset_profile": profile,
        "missing_required_classes": missing, "invalid_rows": invalid[:100],
    }
    result["pass"] = bool(label_files) and not unknown and not missing and not invalid
    return result


def main() -> int:
    mode = "__RUN_MODE__".strip().lower()
    profile = "__DATASET_PROFILE__".strip().lower()
    if mode not in {"quality_gate", *EPOCHS}:
        raise ValueError(f"Unsupported RUN_MODE={mode}")
    import torch
    gpu = {"cuda_available": torch.cuda.is_available(), "count": torch.cuda.device_count()}
    if not gpu["cuda_available"]:
        raise RuntimeError("Kaggle GPU is required")
    yaml_path = find_yaml()
    source_manifests = list(ROOT.rglob("source_manifest.json"))
    for manifest_path in source_manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for source in manifest.get("sources", []):
            if source.get("slug") == "braunge/tt100k" and "minimum-speed pm" in source.get("use", ""):
                raise RuntimeError("Rejected builder V1/V2: pm is mass restriction. Use corrected il* source.")
    audit = audit_dataset(yaml_path, profile)
    dump("preflight.json", {
        "gpu": gpu, "dataset_yaml": str(yaml_path), "run_mode": mode,
        "dataset_profile": profile,
    })
    dump("dataset_audit.json", audit)
    for source in source_manifests:
        dump("source_manifest.json", json.loads(source.read_text(encoding="utf-8")))
        for image in (source.parent / "quality_gate").glob("*.jpg"):
            target = OUT / "quality_gate" / image.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image, target)
    if not audit["pass"]:
        dump("job_status.json", {"status": "DATA_GATE_FAILED", "run_mode": mode})
        raise RuntimeError("Dataset quality gate failed; inspect dataset_audit.json")
    if mode == "quality_gate":
        dump("job_status.json", {"status": "QUALITY_GATE_READY", "run_mode": mode})
        return 0
    if "__QUALITY_GATE_APPROVED__" != "PASS":
        raise RuntimeError("Training requires QUALITY_GATE_APPROVED=PASS")

    try:
        from ultralytics import YOLO
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "ultralytics==8.3.203"]
        )
        from ultralytics import YOLO
    model = YOLO(os.getenv("BASE_MODEL", "yolo11s.pt"))
    import yaml
    portable = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    portable["path"] = str(yaml_path.parent)
    resolved_yaml = OUT / "resolved_dataset.yaml"
    resolved_yaml.write_text(yaml.safe_dump(portable), encoding="utf-8")
    result = model.train(
        data=str(resolved_yaml), epochs=EPOCHS[mode], imgsz=960, batch=-1,
        device=0, workers=4, project=str(OUT), name="train", exist_ok=True,
        seed=162, deterministic=True, cache=False,
    )
    best = Path(result.save_dir) / "weights" / "best.pt"
    exported = Path(model.__class__(str(best)).export(format="onnx", imgsz=960, simplify=True))
    metrics = {
        "run_mode": mode, "epochs": EPOCHS[mode], "best_pt": str(best),
        "best_pt_sha256": sha256(best), "best_onnx": str(exported),
        "best_onnx_sha256": sha256(exported),
    }
    dump("training_manifest.json", metrics)
    dump("job_status.json", {"status": "TRAINING_COMPLETE", **metrics})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
