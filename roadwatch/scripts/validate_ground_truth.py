from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from roadwatch.ground_truth import validate_ground_truth  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate RoadWatch timestamp ground truth")
    parser.add_argument("--input", default="evaluation/event_ground_truth.json")
    args = parser.parse_args()
    payload = json.loads((PROJECT_ROOT / args.input).read_text(encoding="utf-8"))
    errors = validate_ground_truth(payload)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
