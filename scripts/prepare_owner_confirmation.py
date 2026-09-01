from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def prepare(payload: dict) -> dict:
    result = copy.deepcopy(payload)
    prepared_at = datetime.now(timezone.utc).isoformat()
    for window in result["windows"]:
        window["owner_confirmation"] = {
            "proposed_decision": "accept_ai_proposal",
            "status": "pending_owner_confirmation",
            "owner": None,
            "confirmed_at": None,
            "changes": [],
        }
    result["owner_review_draft"] = {
        "status": "ready_for_owner_confirmation",
        "prepared_at": prepared_at,
        "default_policy": "All unchanged windows will be accepted only after explicit owner confirmation.",
        "important": "This draft is not Human-verified and cannot pass the RW-02 promotion gate.",
        "windows_ready": len(result["windows"]),
    }
    result["summary"]["status"] = "owner_confirmation_pending"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare accept-by-default RW-02 owner draft")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.ai_provisional.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.owner_review_draft.json",
    )
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = prepare(payload)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["owner_review_draft"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
