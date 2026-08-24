"""Export only the promotion artifacts from the large Object V2 Kaggle output."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


INPUT = Path("/kaggle/input")
OUTPUT = Path("/kaggle/working/roadwatch_object_v2_export")
SOURCE_SLUG = "roadwatch-object-detector-v2-target-domain"
ARTIFACTS = {
    "best.pt": "roadwatch_objects_v2.pt",
    "best.onnx": "roadwatch_objects_v2.onnx",
    "job_status.json": "job_status.json",
    "pseudo_label_quality_gate.json": "pseudo_label_quality_gate.json",
    "results.csv": "training_results.csv",
    "args.yaml": "training_args.yaml",
    "confusion_matrix.png": "confusion_matrix.png",
    "confusion_matrix_normalized.png": "confusion_matrix_normalized.png",
    "results.png": "training_curves.png",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_artifacts(input_root: Path) -> dict[str, Path]:
    selected: dict[str, Path] = {}
    for source_name in ARTIFACTS:
        matches = list(input_root.rglob(source_name))
        preferred = [path for path in matches if SOURCE_SLUG in str(path)] or matches
        if not preferred:
            continue
        selected[source_name] = max(preferred, key=lambda path: path.stat().st_mtime)
    return selected


def main() -> int:
    selected = select_artifacts(INPUT)
    missing_required = sorted({"best.pt", "best.onnx", "job_status.json"} - set(selected))
    if missing_required:
        raise FileNotFoundError(f"Missing required Object V2 artifacts: {missing_required}")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_kernel": "lekimnam/roadwatch-object-detector-v2-target-domain",
        "source_version": 4,
        "promotion_status": "blocked_pending_human_pseudo_label_review_and_event_regression",
        "artifacts": [],
    }
    total_bytes = 0
    for source_name, source in selected.items():
        destination = OUTPUT / ARTIFACTS[source_name]
        shutil.copy2(source, destination)
        size = destination.stat().st_size
        total_bytes += size
        manifest["artifacts"].append(
            {
                "name": destination.name,
                "size_bytes": size,
                "sha256": sha256_file(destination),
            }
        )
    if total_bytes > 250 * 1024 * 1024:
        raise RuntimeError(f"Artifact export unexpectedly exceeds 250 MiB: {total_bytes}")
    manifest["total_bytes"] = total_bytes
    (OUTPUT / "artifact_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
