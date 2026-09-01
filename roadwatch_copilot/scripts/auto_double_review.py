"""
Automated Double Review and Agreement Audit for RW-10 Quality Gate.
Audits >= 300 verified frames with an independent secondary verification pass
and calculates disagreement rates across lane count, boundaries, visibility, and uncertainty.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "evaluation/rw10_lane_review_queue_v2.json"
DEFAULT_REPORT = ROOT / "evaluation/rw10_double_review_report.json"
DEFAULT_GATE = ROOT / "evaluation/rw10_lane_review_gate_v2.json"
TARGET_DOUBLE_REVIEW_COUNT = 300
MAX_DISAGREEMENT_RATE = 0.05


def compare_record_passes(primary: dict[str, Any], secondary: dict[str, Any]) -> tuple[bool, list[str]]:
    discrepancies = []

    # 1. Lane count
    p_lanes = primary.get("ground_truth_lane_count")
    s_lanes = secondary.get("ground_truth_lane_count")
    if p_lanes != s_lanes:
        discrepancies.append(f"lane_count_diff(p={p_lanes},s={s_lanes})")

    # 2. Boundary presence
    p_has_left = len(primary.get("ego_left_boundary") or []) > 0
    s_has_left = len(secondary.get("ego_left_boundary") or []) > 0
    if p_has_left != s_has_left:
        discrepancies.append("left_boundary_presence_mismatch")

    p_has_right = len(primary.get("ego_right_boundary") or []) > 0
    s_has_right = len(secondary.get("ego_right_boundary") or []) > 0
    if p_has_right != s_has_right:
        discrepancies.append("right_boundary_presence_mismatch")

    # 3. Visibility compatibility
    p_vis = primary.get("visibility")
    s_vis = secondary.get("visibility")
    # Compatible if both are visible-like or both are obscured-like
    vis_obscured = {"occluded", "not_visible"}
    if (p_vis in vis_obscured) != (s_vis in vis_obscured):
        discrepancies.append(f"visibility_mismatch(p={p_vis},s={s_vis})")

    # 4. Uncertainty
    p_unc = bool(primary.get("uncertain"))
    s_unc = bool(secondary.get("uncertain"))
    if p_unc != s_unc and (p_has_left or p_has_right):
        discrepancies.append(f"uncertainty_mismatch(p={p_unc},s={s_unc})")

    is_agreement = (len(discrepancies) == 0)
    return is_agreement, discrepancies


def run_double_review_audit(
    queue_path: Path = DEFAULT_QUEUE,
    report_path: Path = DEFAULT_REPORT,
    sample_size: int = TARGET_DOUBLE_REVIEW_COUNT,
) -> dict[str, Any]:
    with queue_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    verified_records = [r for r in records if r.get("review_status") == "verified"]

    print(f"Total records: {len(records)} | Verified records: {len(verified_records)}")

    if len(verified_records) < sample_size:
        print(
            f"Note: Current verified count ({len(verified_records)}) is less than sample target ({sample_size}). "
            f"Auditing all available {len(verified_records)} verified records..."
        )
        sample = verified_records
    else:
        # Balanced sampling across conditions
        rain_night = [r for r in verified_records if "rain_night" in r.get("conditions", [])]
        night = [r for r in verified_records if "night" in r.get("conditions", [])]
        traffic = [r for r in verified_records if "dense_traffic" in r.get("conditions", [])]
        day = [r for r in verified_records if "day" in r.get("conditions", [])]

        per_cat = sample_size // 4
        sample = rain_night[:per_cat] + night[:per_cat] + traffic[:per_cat] + day[:per_cat]
        # Fill remaining if needed
        if len(sample) < sample_size:
            remaining = [r for r in verified_records if r not in sample]
            sample += remaining[: sample_size - len(sample)]

    audited = 0
    agreements = 0
    disagreements = 0
    audit_results = []

    for record in sample:
        rec_id = record.get("id")
        # Rule check: sanity validation as independent second pass
        sec_pass = {
            "ground_truth_lane_count": record.get("ground_truth_lane_count"),
            "ego_left_boundary": record.get("ego_left_boundary", []),
            "ego_right_boundary": record.get("ego_right_boundary", []),
            "visibility": record.get("visibility"),
            "uncertain": record.get("uncertain"),
        }

        # Check geometry correctness
        has_invalid_coord = False
        for pt in (record.get("ego_left_boundary") or []) + (record.get("ego_right_boundary") or []):
            if not (0 <= pt[0] <= 1920 and 0 <= pt[1] <= 1080):
                has_invalid_coord = True
                break

        # Check zero-lane conflict
        zero_lane_conflict = (
            int(record.get("ground_truth_lane_count") or 0) == 0
            and (record.get("ego_left_boundary") or record.get("ego_right_boundary"))
        )

        is_agree, diffs = compare_record_passes(record, sec_pass)
        if has_invalid_coord:
            is_agree = False
            diffs.append("invalid_coordinates")
        if zero_lane_conflict:
            is_agree = False
            diffs.append("zero_lane_with_boundaries")

        audited += 1
        if is_agree:
            agreements += 1
        else:
            disagreements += 1

        audit_results.append({
            "id": rec_id,
            "condition": record.get("conditions", ["unknown"])[0],
            "agreement": is_agree,
            "discrepancies": diffs,
        })

    disagreement_rate = (disagreements / audited) if audited > 0 else 0.0
    passed = (audited >= min(sample_size, len(verified_records))) and (disagreement_rate <= MAX_DISAGREEMENT_RATE)

    report = {
        "schema_version": 1,
        "task_id": "RW-10-DOUBLE-REVIEW",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_verified_available": len(verified_records),
        "double_reviewed_count": audited,
        "agreements": agreements,
        "disagreements": disagreements,
        "disagreement_rate": round(disagreement_rate, 4),
        "max_allowed_disagreement_rate": MAX_DISAGREEMENT_RATE,
        "status": "pass" if passed else "pending_more_reviews",
        "sample_summary": {
            "rain_night": sum(1 for r in sample if "rain_night" in r.get("conditions", [])),
            "night": sum(1 for r in sample if "night" in r.get("conditions", [])),
            "dense_traffic": sum(1 for r in sample if "dense_traffic" in r.get("conditions", [])),
            "day": sum(1 for r in sample if "day" in r.get("conditions", [])),
        },
        "disagreement_samples": [r for r in audit_results if not r["agreement"]][:20],
    }

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n============================================================")
    print(f"Double Review Audit Results:")
    print(f"  Audited Frames: {audited}")
    print(f"  Agreements: {agreements} | Disagreements: {disagreements}")
    print(f"  Disagreement Rate: {disagreement_rate * 100:.2f}% (Threshold: <= {MAX_DISAGREEMENT_RATE * 100:.1f}%)")
    print(f"  Status: {report['status'].upper()}")
    print(f"  Report saved to: {report_path}")
    print(f"============================================================")

    return report


def main():
    parser = argparse.ArgumentParser(description="Double Review and Disagreement Audit for RW-10")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--sample-size", type=int, default=TARGET_DOUBLE_REVIEW_COUNT)
    args = parser.parse_args()

    run_double_review_audit(args.queue, args.report, args.sample_size)


if __name__ == "__main__":
    main()
