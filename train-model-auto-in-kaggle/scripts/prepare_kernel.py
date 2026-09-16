from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from common import CONTROL_ROOT, load_json, sha256, utc_now, write_json


def patch_training_script(text: str, detector_epochs: int, classifier_epochs: int) -> str:
    text, detector_count = re.subn(r"detector\.train\((.*?)epochs=35,", rf"detector.train(\1epochs={detector_epochs},", text, count=1, flags=re.S)
    text, classifier_count = re.subn(r"classifier\.train\((.*?)epochs=30,", rf"classifier.train(\1epochs={classifier_epochs},", text, count=1, flags=re.S)
    if detector_count != 1 or classifier_count != 1:
        raise RuntimeError("Training epoch anchors changed; refusing unsafe patch")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--output", default="build/kernel")
    args = parser.parse_args()
    if not args.owner.strip() or "/" in args.owner:
        raise ValueError("Kaggle owner must be the authenticated username")
    config = load_json(Path(args.config))
    source = CONTROL_ROOT.parent / config["source_package"]
    output = Path(args.output)
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(source, output)
    script = output / "roadwatch_train_sign_phase2.py"
    patched = patch_training_script(
        script.read_text(encoding="utf-8"),
        int(config["detector_epochs"]),
        int(config["classifier_epochs"]),
    )
    script.write_text(patched, encoding="utf-8")
    metadata = load_json(output / "kernel-metadata.json")
    metadata.update(
        {
            "id": f"{args.owner}/{config['kernel_slug']}",
            "title": config["kernel_title"],
            "enable_gpu": "true",
            "enable_internet": "true" if config.get("internet_enabled") else "false",
            "machine_shape": config.get("machine_shape", "NvidiaTeslaT4"),
            "dataset_sources": config["dataset_sources"],
        }
    )
    write_json(output / "kernel-metadata.json", metadata)
    manifest = {
        "prepared_at": utc_now(),
        "kernel_ref": metadata["id"],
        "run_mode": config["run_mode"],
        "detector_epochs": config["detector_epochs"],
        "classifier_epochs": config["classifier_epochs"],
        "script_sha256": sha256(script),
        "auto_promote": False,
    }
    write_json(output / "roadwatch_run_manifest.json", manifest)
    print(json.dumps(manifest))


if __name__ == "__main__":
    raise SystemExit(main())
