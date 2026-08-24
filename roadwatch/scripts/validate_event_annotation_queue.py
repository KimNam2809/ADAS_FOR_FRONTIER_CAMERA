from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.annotation_gate import validate_annotation_queue  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RW-02 Human Quality Gate")
    parser.add_argument(
        "--queue",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "dashcam_annotation_queue.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.queue.read_text(encoding="utf-8"))
    report = validate_annotation_queue(payload)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
