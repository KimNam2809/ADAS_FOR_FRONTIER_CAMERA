from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile phase-2.1 train-only VRU replication")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    counts: Counter[int] = Counter()
    original = 0
    balanced = 0
    with args.manifest.open(encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if record["source"] not in {"bdd100k", "dawn"} or record["split"] != "train":
                continue
            classes = {int(box["class_id"]) for box in record["boxes"]}
            multiplier = max(
                (3 if class_id in {1, 3} else 2 if class_id == 2 else 1 for class_id in classes),
                default=1,
            )
            original += 1
            balanced += multiplier
            counts[multiplier] += 1
    print(
        json.dumps(
            {
                "original_train_images": original,
                "balanced_train_entries": balanced,
                "extra_entries": balanced - original,
                "multipliers": dict(sorted(counts.items())),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
