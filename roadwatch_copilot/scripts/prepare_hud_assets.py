"""Convert generated green-screen HUD vehicles into compact transparent PNGs.

The generated source files stay outside the repository. Only the cropped,
optimized runtime assets are written to ``frontend/public/hud``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def convert(source: Path, output: Path, max_side: int) -> None:
    image = Image.open(source).convert("RGBA")
    pixels = np.asarray(image).copy()
    red = pixels[..., 0].astype(np.int16)
    green = pixels[..., 1].astype(np.int16)
    blue = pixels[..., 2].astype(np.int16)
    dominance = green - np.maximum(red, blue)
    green_screen = (green > 80) & (dominance > 12)

    # Keep a soft antialiased edge while removing the uniform chroma backdrop.
    alpha = np.clip(255 - (dominance - 12) * 9, 0, 255).astype(np.uint8)
    pixels[..., 3] = np.where(green_screen, alpha, pixels[..., 3])
    pixels[..., 1] = np.where(
        green_screen,
        np.minimum(green, np.maximum(red, blue) + 8),
        green,
    ).astype(np.uint8)

    result = Image.fromarray(pixels, mode="RGBA")
    bbox = result.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"No foreground found in {source}")
    result = result.crop(bbox)

    padding = max(6, int(max(result.size) * 0.025))
    padded = Image.new(
        "RGBA", (result.width + padding * 2, result.height + padding * 2)
    )
    padded.alpha_composite(result, (padding, padding))
    ratio = min(1.0, max_side / max(padded.size))
    if ratio < 1.0:
        padded = padded.resize(
            (max(1, round(padded.width * ratio)), max(1, round(padded.height * ratio))),
            Image.Resampling.LANCZOS,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    padded.save(output, format="PNG", optimize=True, compress_level=9)
    print(f"{source.name} -> {output} ({padded.width}x{padded.height})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-side", type=int, default=360)
    args = parser.parse_args()
    convert(args.source, args.output, args.max_side)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
