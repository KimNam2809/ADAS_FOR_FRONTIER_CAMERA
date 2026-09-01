from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def finalize(payload: dict, reviewer: str, confirmed: bool) -> dict:
    if not confirmed:
        raise ValueError("Explicit --confirm-all-unchanged is required")
    reviewer = reviewer.strip()
    if len(reviewer) < 2:
        raise ValueError("A real reviewer identifier is required")
    confirmed_at = datetime.now(timezone.utc).isoformat()
    for window in payload["windows"]:
        owner = window.get("owner_confirmation", {})
        if owner.get("proposed_decision") == "reject_ai_proposal":
            raise ValueError(
                f"{window['window_id']} is rejected; apply corrections before finalizing"
            )
        owner.update(
            {
                "status": "confirmed_by_owner",
                "owner": reviewer,
                "confirmed_at": confirmed_at,
            }
        )
        window["owner_confirmation"] = owner
        window["primary_review"] = {
            "reviewer": reviewer,
            "status": "verified",
            "reviewed_at": confirmed_at,
            "basis": "Owner reviewed full-motion video and accepted unchanged AI proposal",
        }
        for event in window.get("events", []):
            event["review_status"] = "verified"
        if window.get("secondary_review", {}).get("required"):
            window["secondary_review"]["status"] = "pending"
    payload["owner_review_draft"]["status"] = "owner_confirmed"
    payload["owner_review_draft"]["confirmed_by"] = reviewer
    payload["owner_review_draft"]["confirmed_at"] = confirmed_at

    verified_seconds = 0.0
    verified_negative_seconds = 0.0
    event_counts: Counter[str] = Counter()
    pending_secondary_windows = 0
    for window in payload["windows"]:
        if window.get("primary_review", {}).get("status") != "verified":
            continue
        coverage = (
            float(window.get("end_seconds", 0)) - float(window.get("start_seconds", 0))
            if window.get("exhaustive")
            else 0.0
        )
        verified_seconds += coverage
        if window.get("is_negative") is True:
            verified_negative_seconds += coverage
        for event in window.get("events", []):
            event_counts[str(event.get("event_type", ""))] += 1
        secondary = window.get("secondary_review", {})
        if secondary.get("required") is True and secondary.get("status") != "verified":
            pending_secondary_windows += 1

    minimum_events = 20
    exceptions = payload.setdefault("event_coverage_exceptions", {})
    for event_type in payload.get("policy", {}).get("allowed_event_types", []):
        count = event_counts[event_type]
        if count < minimum_events and not str(exceptions.get(event_type) or "").strip():
            exceptions[event_type] = (
                f"Owner-verified RW-02 sample contains {count}/{minimum_events} required "
                "events; coverage is insufficient and must be expanded before "
                "event-specific model promotion."
            )

    payload["summary"].update(
        {
            "verified_coverage_seconds": round(verified_seconds, 3),
            "verified_negative_seconds": round(verified_negative_seconds, 3),
            "verified_event_counts": dict(event_counts),
            "pending_secondary_windows": pending_secondary_windows,
            "status": (
                "primary_verified_secondary_review_pending"
                if pending_secondary_windows
                else "primary_verified"
            ),
        }
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize explicit RW-02 owner confirmation")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.owner_review_draft.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.owner_verified.json",
    )
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--confirm-all-unchanged", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = finalize(payload, args.reviewer, args.confirm_all_unchanged)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
