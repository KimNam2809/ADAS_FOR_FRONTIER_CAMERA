from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from roadwatch.fallen_rider import dataset_gate, validate_source_catalog  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit RW-08 source catalog and dataset gate")
    parser.add_argument("--catalog", type=Path, default=ROOT / "configs/fallen_rider_sources.json")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/rw08_source_audit.json")
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    errors = validate_source_catalog(catalog)
    target_manifest = (
        json.loads(args.manifest.read_text(encoding="utf-8"))
        if args.manifest and args.manifest.exists()
        else {
            "instances": {},
            "positive_images": 0,
            "negative_images": 0,
            "clip_count": 0,
            "night_or_adverse_clips": 0,
            "video_groups": {},
            "scenario_groups": {},
            "licenses_approved": False,
            "forward_dashcam_test_set_present": False,
            "validation_real_positives": 0,
            "validation_total_positives": 0,
            "test_synthetic_count": -1,
            "test_source_types": [],
            "source_provenance": [],
        }
    )
    gate = dataset_gate(target_manifest)
    report = {
        "schema_version": 1,
        "task_id": "RW-08",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_status": "pass" if not errors else "fail",
        "catalog_errors": errors,
        "sources": catalog.get("sources", []),
        "dataset_gate": gate,
        "training_allowed": not errors and gate["status"] == "pass",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
