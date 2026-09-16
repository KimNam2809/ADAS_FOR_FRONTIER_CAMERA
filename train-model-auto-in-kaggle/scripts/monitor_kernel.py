from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from common import normalize_status, require_kaggle_env, run, set_github_output, utc_now, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel", required=True)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--timeout-minutes", type=int, default=5)
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--output", default="build/status.json")
    args = parser.parse_args()
    require_kaggle_env()
    deadline = time.monotonic() + max(0, args.timeout_minutes) * 60
    status, details = "UNKNOWN", ""
    while True:
        result = run(["kaggle", "kernels", "status", args.kernel], check=False)
        details = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
        status = normalize_status(details)
        if not args.wait or status in {"COMPLETE", "ERROR"} or time.monotonic() >= deadline:
            break
        time.sleep(max(5, args.interval_seconds))
    report = {"kernel_ref": args.kernel, "status": status, "checked_at": utc_now(), "details": details[-1000:]}
    write_json(Path(args.output), report)
    set_github_output("status", status)
    print(json.dumps(report))
    return 2 if status == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())

