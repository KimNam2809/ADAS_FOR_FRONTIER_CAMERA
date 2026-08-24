from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.promotion import profile_metrics, promotion_gate  # noqa: E402
from roadwatch.regression import sha256_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RW-04 object candidate promotion")
    parser.add_argument("--baseline", default="reports/rw03-regression-final.json")
    parser.add_argument("--candidate", default="reports/rw04-candidate-regression.json")
    parser.add_argument("--ground-truth", default="evaluation/regression_ground_truth.json")
    parser.add_argument("--output", default="evaluation/rw04_object_promotion.json")
    args = parser.parse_args()

    baseline_path = PROJECT_ROOT / args.baseline
    candidate_path = PROJECT_ROOT / args.candidate
    truth_path = PROJECT_ROOT / args.ground_truth
    baseline_report = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate_report = json.loads(candidate_path.read_text(encoding="utf-8"))
    ground_truth = json.loads(truth_path.read_text(encoding="utf-8"))
    baseline = profile_metrics(baseline_report, ground_truth)
    candidate = profile_metrics(candidate_report, ground_truth)
    gate = promotion_gate(baseline, candidate)
    result = {
        "schema_version": 1,
        "task_id": "RW-04",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline_profile": "baseline_coco",
        "candidate_profile": candidate_report.get("object_profile", "roadwatch_objects_v1_1"),
        "inputs": {
            "baseline": {"path": args.baseline, "sha256": sha256_file(baseline_path)},
            "candidate": {"path": args.candidate, "sha256": sha256_file(candidate_path)},
            "ground_truth": {"path": args.ground_truth, "sha256": sha256_file(truth_path)},
        },
        "baseline": baseline,
        "candidate": candidate,
        "promotion_gate": gate,
        "active_profile_after_gate": "baseline_coco",
    }
    output = PROJECT_ROOT / args.output
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
