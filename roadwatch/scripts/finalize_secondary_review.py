from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def finalize_secondary(
    payload: dict,
    reviewer: str,
    reported_by: str,
    confirmed_all_pass: bool,
) -> dict:
    if not confirmed_all_pass:
        raise ValueError("Explicit --confirm-all-critical-pass is required")
    reviewer = reviewer.strip()
    reported_by = reported_by.strip()
    if len(reviewer) < 2 or len(reported_by) < 2:
        raise ValueError("Reviewer and reporter identifiers are required")

    reviewed_at = datetime.now(timezone.utc).isoformat()
    verified_windows: list[str] = []
    for window in payload.get("windows", []):
        secondary = window.get("secondary_review", {})
        if secondary.get("required") is not True:
            continue
        secondary.update(
            {
                "reviewer": reviewer,
                "status": "verified",
                "reviewed_at": reviewed_at,
                "agrees_with_primary": True,
                "confirmation_source": f"reported_by:{reported_by}",
            }
        )
        window["secondary_review"] = secondary
        verified_windows.append(str(window.get("window_id")))

    if not verified_windows:
        raise ValueError("No critical windows require secondary review")

    payload["secondary_review_confirmation"] = {
        "status": "confirmed_all_pass",
        "reviewer": reviewer,
        "reported_by": reported_by,
        "confirmed_at": reviewed_at,
        "window_ids": verified_windows,
    }
    payload.setdefault("summary", {}).update(
        {
            "pending_secondary_windows": 0,
            "verified_secondary_windows": len(verified_windows),
            "status": "human_quality_gate_ready",
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize RW-02 independent secondary review")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.owner_verified.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.ground_truth.json",
    )
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reported-by", required=True)
    parser.add_argument("--confirm-all-critical-pass", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = finalize_secondary(
        payload,
        reviewer=args.reviewer,
        reported_by=args.reported_by,
        confirmed_all_pass=args.confirm_all_critical_pass,
    )
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["secondary_review_confirmation"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
