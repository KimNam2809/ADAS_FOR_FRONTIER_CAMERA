from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import load_json, require_kaggle_env, run, set_github_output, utc_now, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--output", default="build/submission.json")
    args = parser.parse_args()
    require_kaggle_env()
    package = Path(args.package)
    metadata = load_json(package / "kernel-metadata.json")
    result = run(["kaggle", "kernels", "push", "-p", str(package)])
    report = {
        "status": "SUBMITTED",
        "submitted_at": utc_now(),
        "kernel_ref": metadata["id"],
        "url": f"https://www.kaggle.com/code/{metadata['id'].replace('/', '/')}",
        "cli_summary": result.stdout.strip()[-500:],
        "auto_promote": False,
    }
    write_json(Path(args.output), report)
    set_github_output("kernel_ref", report["kernel_ref"])
    set_github_output("kernel_url", report["url"])
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

