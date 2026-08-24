from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.config import ConfigManager  # noqa: E402
from roadwatch.release import verify_release  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify RoadWatch release/model consistency")
    parser.add_argument(
        "--defaults-only",
        action="store_true",
        help="Ignore configs/runtime.json and validate the tracked defaults",
    )
    parser.add_argument(
        "--skip-hashes",
        action="store_true",
        help="Check files and profiles without reading every model byte",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    runtime_path = PROJECT_ROOT / "configs" / "__release_defaults_only__.json"
    manager = ConfigManager(runtime_path=runtime_path) if args.defaults_only else ConfigManager()
    report = verify_release(manager.snapshot(), verify_hashes=not args.skip_hashes)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
