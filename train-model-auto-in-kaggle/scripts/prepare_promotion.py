from __future__ import annotations

import argparse
from pathlib import Path

from common import load_json, utc_now, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare, never execute, a RoadWatch model promotion")
    parser.add_argument("--evaluation", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--human-approved", action="store_true")
    parser.add_argument("--output", default="build/promotion_request.json")
    args = parser.parse_args()
    evaluation = load_json(Path(args.evaluation))
    ready = evaluation.get("status") == "PASS_PENDING_HUMAN_GATE" and args.human_approved
    report = {
        "candidate_id": args.candidate_id,
        "prepared_at": utc_now(),
        "human_approved": args.human_approved,
        "status": "READY_FOR_MANUAL_PROMOTION_PR" if ready else "BLOCKED",
        "auto_promote": False,
        "active_model_changed": False,
    }
    write_json(Path(args.output), report)
    print(report["status"])
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
