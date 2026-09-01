"""
Lane Quality Gate Verification and Compliance Auditor (RW-10).
Evaluates all criteria required before launching Lane fine-tuning.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "evaluation/rw10_lane_review_queue_v2.json"
DEFAULT_GATE = ROOT / "evaluation/rw10_lane_review_gate_v2.json"
DEFAULT_DOUBLE_REPORT = ROOT / "evaluation/rw10_double_review_report.json"

FRAME_WIDTH = 1920
FRAME_HEIGHT = 1080


def audit_quality_gate(
    queue_path: Path = DEFAULT_QUEUE,
    gate_path: Path = DEFAULT_GATE,
    double_report_path: Path = DEFAULT_DOUBLE_REPORT,
) -> dict[str, Any]:
    with queue_path.open("r", encoding="utf-8") as f:
        queue_data = json.load(f)

    records = queue_data.get("records", [])
    total_records = len(records)
    verified_records = [r for r in records if r.get("review_status") == "verified"]
    pending_records = [r for r in records if r.get("review_status") == "pending"]
    recheck_records = [r for r in records if r.get("review_status") == "needs_recheck"]

    # 1. Condition counts
    night_verified = sum(
        1 for r in verified_records
        if "night" in r.get("conditions", [])
    )
    rain_night_verified = sum(
        1 for r in verified_records
        if "rain_night" in r.get("conditions", [])
    )
    multi_lane_verified = sum(
        1 for r in verified_records
        if (r.get("ground_truth_lane_count") or 0) > 1
    )
    faded_missing_verified = sum(
        1 for r in verified_records
        if (r.get("uncertain") is True or r.get("visibility") in ["partial", "occluded", "not_visible"])
    )

    # 2. Coordinate sanity check
    invalid_coords_count = 0
    for r in verified_records:
        for pt in (r.get("ego_left_boundary") or []) + (r.get("ego_right_boundary") or []):
            if not (0 <= pt[0] <= FRAME_WIDTH and 0 <= pt[1] <= FRAME_HEIGHT):
                invalid_coords_count += 1

    # 3. Split overlap check
    split_sources: dict[str, set[str]] = {}
    for r in records:
        split_sources.setdefault(str(r.get("split")), set()).add(str(r.get("source")))
    split_values = list(split_sources.values())
    has_split_overlap = any(
        split_values[i] & split_values[j]
        for i in range(len(split_values))
        for j in range(i + 1, len(split_values))
    )

    # 4. Double review report check
    double_reviewed_count = 0
    disagreement_rate = 1.0
    if double_report_path.exists():
        try:
            d_rep = json.loads(double_report_path.read_text(encoding="utf-8"))
            double_reviewed_count = d_rep.get("double_reviewed_count", 0)
            disagreement_rate = d_rep.get("disagreement_rate", 1.0)
        except Exception:
            pass

    # Targets
    target_verified = 3000
    target_night = 500
    target_rain_night = 400
    target_multi_lane = 1000
    target_faded_missing = 400
    target_double_review = 300
    max_disagreement = 0.05

    criteria = [
        {
            "criterion": "Verified frames >= 3,000",
            "current": len(verified_records),
            "target": target_verified,
            "passed": len(verified_records) >= target_verified,
        },
        {
            "criterion": "Night verified >= 500",
            "current": night_verified,
            "target": target_night,
            "passed": night_verified >= target_night,
        },
        {
            "criterion": "Rain/Rain-night verified >= 400",
            "current": rain_night_verified,
            "target": target_rain_night,
            "passed": rain_night_verified >= target_rain_night,
        },
        {
            "criterion": "Multi-lane verified >= 1,000",
            "current": multi_lane_verified,
            "target": target_multi_lane,
            "passed": multi_lane_verified >= target_multi_lane,
        },
        {
            "criterion": "Faded/missing marking >= 400",
            "current": faded_missing_verified,
            "target": target_faded_missing,
            "passed": faded_missing_verified >= target_faded_missing,
        },
        {
            "criterion": "Double-reviewed frames >= 300",
            "current": double_reviewed_count,
            "target": target_double_review,
            "passed": double_reviewed_count >= target_double_review,
        },
        {
            "criterion": "Review disagreement <= 5%",
            "current": f"{disagreement_rate * 100:.2f}%",
            "target": f"<= {max_disagreement * 100:.1f}%",
            "passed": disagreement_rate <= max_disagreement,
        },
        {
            "criterion": "Invalid coordinates == 0",
            "current": invalid_coords_count,
            "target": 0,
            "passed": invalid_coords_count == 0,
        },
        {
            "criterion": "Split leakage == 0",
            "current": "No overlap" if not has_split_overlap else "OVERLAP DETECTED",
            "target": "No overlap",
            "passed": not has_split_overlap,
        },
    ]

    all_passed = all(c["passed"] for c in criteria)

    gate_result = {
        "schema_version": 2,
        "task_id": "RW-10",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ready_for_finetune" if all_passed else "in_progress_pending_verification",
        "training_blocked": not all_passed,
        "summary": {
            "total_records_in_queue": total_records,
            "verified": len(verified_records),
            "pending": len(pending_records),
            "needs_recheck": len(recheck_records),
        },
        "criteria": criteria,
        "human_action": "Proceed with fine-tune pilot" if all_passed else "Continue review pipeline to fulfill remaining criteria.",
    }

    gate_path.write_text(json.dumps(gate_result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n============================================================")
    print(f"       LANE QUALITY GATE AUDIT REPORT (RW-10)               ")
    print(f"============================================================")
    for idx, c in enumerate(criteria, 1):
        status_sym = "[PASS]" if c["passed"] else "[PENDING]"
        print(f"  {idx:2d}. {c['criterion']:<38s} | Current: {str(c['current']):<10s} | {status_sym}")
    print(f"------------------------------------------------------------")
    print(f"  OVERALL GATE STATUS: {gate_result['status'].upper()}")
    print(f"  TRAINING BLOCKED:    {gate_result['training_blocked']}")
    print(f"  Gate report updated: {gate_path}")
    print(f"============================================================")

    return gate_result


def main():
    parser = argparse.ArgumentParser(description="Verify Lane Quality Gate RW-10")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE)
    parser.add_argument("--double-report", type=Path, default=DEFAULT_DOUBLE_REPORT)
    args = parser.parse_args()

    audit_quality_gate(args.queue, args.gate, args.double_report)


if __name__ == "__main__":
    main()
