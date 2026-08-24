"""RoadWatch Object V2 target-domain adaptation on Kaggle GPU."""

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


INPUT = Path("/kaggle/input")
WORK = Path("/kaggle/working")
TEMP = Path("/kaggle/temp")
OUTPUT = WORK / "roadwatch_object_v2"
DATASET = TEMP / "roadwatch_object_v2_dataset"
TARGET = TEMP / "roadwatch_target_videos"
FRAMES = TEMP / "roadwatch_target_frames"
RUN = OUTPUT / "roadwatch_objects_v2"
CANONICAL = ["person", "rider", "bicycle", "motorcycle", "car", "bus", "truck"]
ALLOWED_SOURCES = {"bdd100k", "dawn"}
EXPECTED_BASE = {"train": 70796, "val": 10104, "test": 20101}
VIDEO_FOLDER_ID = "1UCGEaSL_ZNqAZ5X_VIAgTle1fSUA291g"
TARGET_VIDEOS = {
    "dashcam_vietnam.mp4",
    "dashcam_vietnam_night.mp4",
    "dashcam_vietnam_rain+night.mp4",
    "dashcam_vietnam_traffic_multi.mp4",
    "test_video1.mp4",
    "test_video5.mp4",
    "video_test.mp4",
}
CONFIDENCE = {
    "person": 0.70,
    "rider": 0.72,
    "bicycle": 0.70,
    "motorcycle": 0.72,
    "car": 0.75,
    "bus": 0.75,
    "truck": 0.75,
}
HARD_WINDOWS = {
    "test_video1.mp4": [(8.0, 24.0), (26.0, 38.0)],
    "test_video5.mp4": [(4.0, 20.0), (31.0, 40.0)],
    "video_test.mp4": [(10.0, 22.0)],
    "dashcam_vietnam_night.mp4": [(4.0, 14.0)],
}
SEED = 2809
BACKGROUND_SAMPLING_FPS = 2


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_packages() -> dict[str, str]:
    packages = {"ultralytics": "8.4.119", "gdown": "5.2.0"}
    for package, version in packages.items():
        try:
            __import__(package)
        except ImportError:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", f"{package}=={version}"],
                check=True,
            )
    import cv2
    import torch
    import ultralytics

    if not torch.cuda.is_available():
        raise RuntimeError("Kaggle CUDA GPU is mandatory; CPU training is forbidden")
    devices = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    if not any("T4" in item.upper() or "P100" in item.upper() for item in devices):
        raise RuntimeError(f"Expected T4/P100 accelerator, found {devices}")
    return {
        "torch": torch.__version__,
        "ultralytics": ultralytics.__version__,
        "opencv": cv2.__version__,
        "devices": devices,
    }


def find_file(filename: str, preferred: str) -> Path:
    preferred_matches = [p for p in INPUT.rglob(filename) if preferred in str(p)]
    matches = preferred_matches or list(INPUT.rglob(filename))
    if not matches:
        raise FileNotFoundError(f"Missing Kaggle input {filename!r} from {preferred!r}")
    return max(matches, key=lambda item: item.stat().st_mtime)


def resolve_base_image(original: str) -> Path:
    direct = Path(original)
    if direct.exists():
        return direct
    for slug in ("bdd100k-yolo", "dawn-detection-in-adverse-weather-nature"):
        if slug not in direct.parts:
            continue
        relative = Path(*direct.parts[direct.parts.index(slug) + 1 :])
        for root in INPUT.rglob(slug):
            candidate = root / relative
            if candidate.exists():
                return candidate
    raise FileNotFoundError(original)


def materialize_base(manifest: Path) -> dict:
    counts: Counter[str] = Counter()
    instances: Counter[int] = Counter()
    with manifest.open(encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if record["source"] not in ALLOWED_SOURCES:
                continue
            split = record["split"]
            image = resolve_base_image(record["image"])
            token = hashlib.sha1(
                f"{record['content_hash']}|{record['source']}|{record['image']}".encode()
            ).hexdigest()[:20]
            image_target = DATASET / split / "images" / f"base_{token}{image.suffix.lower()}"
            label_target = DATASET / split / "labels" / f"base_{token}.txt"
            image_target.parent.mkdir(parents=True, exist_ok=True)
            label_target.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(image, image_target)
            lines = []
            for box in record["boxes"]:
                class_id = int(box["class_id"])
                instances[class_id] += 1
                lines.append(
                    f"{class_id} "
                    + " ".join(f"{float(box[key]):.8f}" for key in ("cx", "cy", "width", "height"))
                )
            label_target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            counts[split] += 1
            if sum(counts.values()) % 20000 == 0:
                print("base images", dict(counts), flush=True)
    actual = {split: counts[split] for split in EXPECTED_BASE}
    if actual != EXPECTED_BASE:
        raise RuntimeError(f"Base split drift: expected {EXPECTED_BASE}, got {actual}")
    return {
        "images": actual,
        "instances": {CANONICAL[i]: instances[i] for i in range(len(CANONICAL))},
        "validation_or_test_modified": False,
    }


def download_target_videos() -> list[Path]:
    TARGET.mkdir(parents=True, exist_ok=True)
    attached_root = INPUT / "roadwatch-target-domain-videos-v1"
    attached = {path.name: path for path in attached_root.rglob("*.mp4")} if attached_root.exists() else {}
    # Kaggle sanitizes '+' from uploaded filenames. Preserve the canonical
    # RoadWatch name in the pipeline while resolving the attached file safely.
    sanitized_rain = attached.get("dashcam_vietnam_rainnight.mp4")
    if sanitized_rain is not None:
        attached["dashcam_vietnam_rain+night.mp4"] = sanitized_rain
    if TARGET_VIDEOS.issubset(attached):
        return [attached[name] for name in sorted(TARGET_VIDEOS)]

    subprocess.run(
        [
            sys.executable,
            "-m",
            "gdown",
            "--folder",
            f"https://drive.google.com/drive/folders/{VIDEO_FOLDER_ID}",
            "-O",
            str(TARGET),
            "--remaining-ok",
        ],
        check=True,
    )
    discovered = {**attached, **{path.name: path for path in TARGET.rglob("*.mp4")}}
    missing = sorted(TARGET_VIDEOS - set(discovered))
    if missing:
        raise FileNotFoundError(f"Drive folder is missing target videos: {missing}")
    return [discovered[name] for name in sorted(TARGET_VIDEOS)]


def in_hard_window(name: str, second: float) -> bool:
    return any(start <= second <= end for start, end in HARD_WINDOWS.get(name, []))


def background_sample_seconds(duration: float) -> set[float]:
    if duration < 0:
        raise ValueError("Video duration cannot be negative")
    count = int(duration * BACKGROUND_SAMPLING_FPS)
    return {
        round(index / BACKGROUND_SAMPLING_FPS, 3)
        for index in range(count + 1)
    }


def normalize_video_codec(video: Path) -> tuple[Path, str]:
    import cv2

    cap = cv2.VideoCapture(str(video))
    value = int(cap.get(cv2.CAP_PROP_FOURCC) or 0)
    cap.release()
    fourcc = "".join(chr((value >> (8 * index)) & 0xFF) for index in range(4)).strip("\x00")
    if fourcc.upper() not in {"AV01", "AV1"}:
        return video, fourcc
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(f"FFmpeg is required to decode AV1 target video: {video.name}")
    normalized = TARGET / f"{video.stem}_h264.mp4"
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-c:v",
        "libdav1d",
        "-i",
        str(video),
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(normalized),
    ]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        # Some Kaggle images expose an AV1 decoder without the libdav1d alias.
        fallback = command[:4] + command[6:]
        subprocess.run(fallback, check=True)
    if not normalized.exists() or normalized.stat().st_size == 0:
        raise RuntimeError(f"AV1 transcode produced no output: {video.name}")
    return normalized, fourcc


def extract_frames(videos: list[Path]) -> tuple[list[Path], dict]:
    import cv2

    output: list[Path] = []
    profile = {}
    FRAMES.mkdir(parents=True, exist_ok=True)
    for video in videos:
        canonical_name = video.name
        decodable_video, source_codec = normalize_video_codec(video)
        cap = cv2.VideoCapture(str(decodable_video))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps <= 0 or total <= 0:
            raise RuntimeError(f"Unreadable video metadata: {video}")
        duration = total / fps
        seconds = background_sample_seconds(duration)
        for start, end in HARD_WINDOWS.get(canonical_name, []):
            tick = start
            while tick <= min(end, duration):
                seconds.add(round(tick, 3))
                tick += 0.2
        written = 0
        for second in sorted(seconds):
            cap.set(cv2.CAP_PROP_POS_MSEC, second * 1000.0)
            ok, frame = cap.read()
            if not ok:
                continue
            token = f"{Path(canonical_name).stem}_{int(round(second * 1000)):09d}"
            path = FRAMES / f"{token}.jpg"
            cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            output.append(path)
            written += 1
        cap.release()
        profile[canonical_name] = {
            "source_codec": source_codec,
            "decoded_from": decodable_video.name,
            "fps": round(fps, 3),
            "duration_seconds": round(duration, 3),
            "sampled_frames": written,
            "hard_window_sampling_fps": 5,
            "background_sampling_fps": BACKGROUND_SAMPLING_FPS,
        }
    return output, profile


def pseudo_label(frames: list[Path], checkpoint: Path) -> dict:
    from ultralytics import YOLO

    model = YOLO(str(checkpoint))
    names = model.names
    observed_names = [str(names[i]) for i in sorted(names)]
    if observed_names != CANONICAL:
        raise RuntimeError(f"Checkpoint taxonomy drift: {observed_names}")
    accepted_images = 0
    rejected_images = 0
    class_counts: Counter[str] = Counter()
    confidences: list[float] = []
    audit_samples: list[dict] = []
    for start in range(0, len(frames), 64):
        batch = frames[start : start + 64]
        results = model.predict(
            source=[str(path) for path in batch],
            imgsz=768,
            conf=0.25,
            iou=0.60,
            device=0,
            half=True,
            verbose=False,
        )
        for path, result in zip(batch, results):
            height, width = result.orig_shape
            labels = []
            accepted_boxes = []
            for box in result.boxes:
                class_id = int(box.cls.item())
                label = str(names[class_id])
                confidence = float(box.conf.item())
                if confidence < CONFIDENCE[label]:
                    continue
                x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
                box_width = max(0.0, x2 - x1)
                box_height = max(0.0, y2 - y1)
                if box_width * box_height / max(width * height, 1) < 0.00008:
                    continue
                labels.append(
                    f"{class_id} {(x1 + x2) / (2 * width):.8f} {(y1 + y2) / (2 * height):.8f} "
                    f"{box_width / width:.8f} {box_height / height:.8f}"
                )
                class_counts[label] += 1
                confidences.append(confidence)
                accepted_boxes.append({"label": label, "confidence": round(confidence, 4), "bbox": [x1, y1, x2, y2]})
            if not labels:
                rejected_images += 1
                continue
            image_target = DATASET / "train" / "images" / f"target_{path.name}"
            label_target = DATASET / "train" / "labels" / f"target_{path.stem}.txt"
            shutil.copy2(path, image_target)
            label_target.write_text("\n".join(labels) + "\n", encoding="utf-8")
            accepted_images += 1
            if len(audit_samples) < 200:
                audit_samples.append({"image": str(path), "boxes": accepted_boxes})
        print(f"pseudo-labelled {min(start + 64, len(frames))}/{len(frames)}", flush=True)
    gates = {
        "sampled_images_at_least_2500": len(frames) >= 2500,
        "accepted_positive_images_at_least_750": accepted_images >= 750,
        "person_instances_at_least_300": class_counts["person"] >= 300,
        "motorcycle_instances_at_least_300": class_counts["motorcycle"] >= 300,
        "car_instances_at_least_1000": class_counts["car"] >= 1000,
        "mean_confidence_at_least_075": bool(confidences) and sum(confidences) / len(confidences) >= 0.75,
    }
    report = {
        "method": "high-confidence phase2.1 pseudo labels; train-only",
        "sampled_images": len(frames),
        "accepted_positive_images": accepted_images,
        "rejected_ambiguous_or_empty_images": rejected_images,
        "class_instances": dict(class_counts),
        "mean_confidence": round(sum(confidences) / max(len(confidences), 1), 4),
        "gates": gates,
        "training_allowed": all(gates.values()),
        "promotion_allowed": False,
        "promotion_blocker": "human review of target-domain pseudo labels is mandatory",
        "audit_samples": audit_samples,
    }
    write_json(OUTPUT / "pseudo_label_quality_gate.json", report)
    return report


def write_data_yaml() -> Path:
    import yaml

    path = DATASET / "roadwatch-object-v2.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "path": str(DATASET),
                "train": "train/images",
                "val": "val/images",
                "test": "test/images",
                "names": {index: name for index, name in enumerate(CANONICAL)},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def train(data_yaml: Path, checkpoint: Path, gpu_count: int) -> dict:
    from ultralytics import YOLO

    device = "0,1" if gpu_count >= 2 else "0"
    model = YOLO(str(checkpoint))
    model.train(
        data=str(data_yaml),
        epochs=20,
        imgsz=640,
        batch=64 if gpu_count >= 2 else 32,
        device=device,
        workers=8,
        amp=True,
        cache=False,
        seed=SEED,
        deterministic=True,
        patience=8,
        close_mosaic=5,
        lr0=0.001,
        lrf=0.01,
        save_period=5,
        project=str(OUTPUT),
        name="roadwatch_objects_v2",
        exist_ok=True,
        plots=True,
    )
    best = RUN / "weights" / "best.pt"
    if not best.exists():
        raise FileNotFoundError("Training did not produce best.pt")
    metrics = YOLO(str(best)).val(data=str(data_yaml), split="test", imgsz=640, device="0")
    exported = YOLO(str(best)).export(format="onnx", imgsz=640, dynamic=False, simplify=True)
    return {
        "best": str(best),
        "onnx": str(exported),
        "test_precision": float(metrics.box.mp),
        "test_recall": float(metrics.box.mr),
        "test_map50": float(metrics.box.map50),
        "test_map50_95": float(metrics.box.map),
        "promotion_status": "blocked_pending_human_pseudo_label_review_and_event_regression",
    }


def main() -> int:
    started = time.time()
    status: dict = {"status": "running"}
    try:
        versions = ensure_packages()
        manifest = find_file("normalized_manifest.jsonl", "roadwatch-dataset-quality-gate")
        checkpoint = find_file("best.pt", "roadwatch-object-detector-phase-2-1")
        base = materialize_base(manifest)
        videos = download_target_videos()
        frames, video_profile = extract_frames(videos)
        pseudo = pseudo_label(frames, checkpoint)
        if not pseudo["training_allowed"]:
            status = {
                "status": "quality_gate_failed_no_training",
                "versions": versions,
                "base": base,
                "video_profile": video_profile,
                "pseudo_labels": {key: value for key, value in pseudo.items() if key != "audit_samples"},
                "elapsed_hours": round((time.time() - started) / 3600.0, 3),
            }
            write_json(OUTPUT / "job_status.json", status)
            print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)
            return 0
        data_yaml = write_data_yaml()
        training = train(data_yaml, checkpoint, len(versions["devices"]))
        status = {
            "status": "complete_candidate_not_promoted",
            "versions": versions,
            "base": base,
            "video_profile": video_profile,
            "pseudo_labels": {key: value for key, value in pseudo.items() if key != "audit_samples"},
            "training": training,
            "elapsed_hours": round((time.time() - started) / 3600.0, 3),
        }
    except Exception as exc:
        status = {
            "status": "error",
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "elapsed_hours": round((time.time() - started) / 3600.0, 3),
        }
        write_json(OUTPUT / "job_status.json", status)
        print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)
        raise
    write_json(OUTPUT / "job_status.json", status)
    print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
