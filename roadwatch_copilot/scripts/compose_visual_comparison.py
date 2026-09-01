"""Place a visual target and implementation screenshot side by side for QA."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("implementation", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    reference = Image.open(args.reference).convert("RGB")
    implementation = Image.open(args.implementation).convert("RGB")
    if implementation.size != reference.size:
        implementation = implementation.resize(reference.size, Image.Resampling.LANCZOS)
    comparison = Image.new("RGB", (reference.width * 2, reference.height), "white")
    comparison.paste(reference, (0, 0))
    comparison.paste(implementation, (reference.width, 0))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    comparison.save(args.output, quality=92, optimize=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
