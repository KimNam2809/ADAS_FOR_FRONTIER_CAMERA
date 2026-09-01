"""
Master Automation Pipeline Orchestrator for RW-10 Lane Fine-tune Preparation.
Runs dataset expansion, AI auto-review, double-review audit, and Quality Gate verification.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXEC = sys.executable


def run_cmd(args_list: list[str], desc: str) -> bool:
    print(f"\n>>> [PIPELINE STEP]: {desc}")
    print(f"Executing: {' '.join(args_list)}")
    start = time.time()
    proc = subprocess.run(args_list)
    elapsed = time.time() - start
    if proc.returncode != 0:
        print(f"[FAIL] ERROR in step '{desc}' (code {proc.returncode}) after {elapsed:.1f}s")
        return False
    print(f"[PASS] Step '{desc}' completed successfully in {elapsed:.1f}s")
    return True



def step_status():
    run_cmd(
        [PYTHON_EXEC, str(ROOT / "scripts/verify_lane_quality_gate.py")],
        "Audit Lane Quality Gate Status",
    )


def step_expand():
    run_cmd(
        [PYTHON_EXEC, str(ROOT / "scripts/expand_lane_queue.py")],
        "Expand Queue to 3,000 Frames from Source Videos",
    )


def step_auto_review(limit: int | None = None, priority: int | None = None):
    cmd = [PYTHON_EXEC, str(ROOT / "scripts/auto_review_lane_queue.py")]
    if limit is not None:
        cmd.extend(["--max-frames", str(limit)])
    if priority is not None:
        cmd.extend(["--priority", str(priority)])
    run_cmd(cmd, f"Run Gemini AI Auto-Review (Limit: {limit or 'ALL'})")


def step_double_review():
    run_cmd(
        [PYTHON_EXEC, str(ROOT / "scripts/auto_double_review.py")],
        "Execute Double-Review Audit on 300 Frames",
    )


def step_verify_gate():
    repair_ok = run_cmd(
        [PYTHON_EXEC, str(ROOT / "scripts/repair_lane_review_queue_v2.py"), "--dry-run"],
        "Run Safe Coordinate & Queue Repair Dry-Run",
    )
    if repair_ok:
        run_cmd(
            [PYTHON_EXEC, str(ROOT / "scripts/verify_lane_quality_gate.py")],
            "Verify All 10 Lane Quality Gate Conditions",
        )


def main():
    parser = argparse.ArgumentParser(description="Master Automation Pipeline for RW-10 Lane Gate")
    parser.add_argument("--status", action="store_true", help="Print current Quality Gate status")
    parser.add_argument("--expand", action="store_true", help="Expand dataset to 3,000 frames")
    parser.add_argument("--auto-review", action="store_true", help="Run AI auto-review on pending frames")
    parser.add_argument("--limit", type=int, default=None, help="Batch limit for auto-review")
    parser.add_argument("--priority", type=int, default=None, help="Priority filter for auto-review")
    parser.add_argument("--double-review", action="store_true", help="Run double review audit")
    parser.add_argument("--verify-gate", action="store_true", help="Verify Quality Gate")
    parser.add_argument("--all", action="store_true", help="Run all automation steps in sequence")
    args = parser.parse_args()

    if not any([args.status, args.expand, args.auto_review, args.double_review, args.verify_gate, args.all]):
        step_status()
        return

    if args.status:
        step_status()

    if args.expand or args.all:
        step_expand()

    if args.auto_review or args.all:
        step_auto_review(limit=args.limit, priority=args.priority)

    if args.double_review or args.all:
        step_double_review()

    if args.verify_gate or args.all:
        step_verify_gate()


if __name__ == "__main__":
    main()
