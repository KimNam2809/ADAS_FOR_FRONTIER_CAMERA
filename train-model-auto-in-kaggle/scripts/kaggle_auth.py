from __future__ import annotations

import argparse
import json

from common import redact, require_kaggle_env, run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-dataset", action="append", default=[])
    args = parser.parse_args()
    username, _ = require_kaggle_env()
    result = run(["kaggle", "datasets", "list", "--user", username, "--page-size", "1"])
    datasets: dict[str, str] = {}
    for ref in args.check_dataset:
        probe = run(["kaggle", "datasets", "files", ref], check=False)
        datasets[ref] = "accessible" if probe.returncode == 0 else "denied"
    print(json.dumps({"authenticated": True, "username": username, "datasets": datasets}))
    if any(value != "accessible" for value in datasets.values()):
        print(redact("One or more datasets are inaccessible"))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
