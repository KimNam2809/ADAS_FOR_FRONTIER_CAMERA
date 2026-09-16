from __future__ import annotations

import argparse
from pathlib import Path

from common import CONTROL_ROOT, load_json, require_kaggle_env, run, utc_now, write_json


def validate_config(config: dict) -> list[str]:
    errors: list[str] = []
    for field in ("run_mode", "kernel_slug", "source_package", "detector_epochs", "classifier_epochs"):
        if field not in config:
            errors.append(f"missing:{field}")
    if int(config.get("detector_epochs", 0)) < 1 or int(config.get("classifier_epochs", 0)) < 1:
        errors.append("epochs_must_be_positive")
    if not config.get("gpu_required", False):
        errors.append("gpu_must_be_required")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", default="build/preflight.json")
    parser.add_argument("--skip-remote", action="store_true")
    args = parser.parse_args()
    path = Path(args.config)
    config = load_json(path)
    errors = validate_config(config)
    package = CONTROL_ROOT.parent / str(config.get("source_package", ""))
    if not package.is_dir():
        errors.append(f"missing_source_package:{package}")
    username = "offline"
    datasets = {ref: "not_checked" for ref in config.get("dataset_sources", [])}
    if not args.skip_remote:
        username, _ = require_kaggle_env()
        for ref in datasets:
            result = run(["kaggle", "datasets", "files", ref], check=False)
            datasets[ref] = "accessible" if result.returncode == 0 else "denied"
            if result.returncode:
                errors.append(f"dataset_denied:{ref}")
    report = {
        "status": "PASS" if not errors else "FAIL",
        "checked_at": utc_now(),
        "username": username,
        "config": str(path),
        "gpu_required": bool(config.get("gpu_required")),
        "datasets": datasets,
        "errors": errors,
        "local_training_started": False,
    }
    write_json(Path(args.output), report)
    print(f"preflight={report['status']} errors={len(errors)}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())

