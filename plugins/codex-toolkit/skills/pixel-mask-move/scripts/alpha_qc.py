#!/usr/bin/env python3
"""Create a three-background alpha preview and reject suspicious internal holes."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def inspect_alpha(alpha: np.ndarray) -> tuple[str, int, int, int, tuple[str, ...]]:
    """Return a conservative alpha-quality decision; this never repairs pixels."""
    foreground = (alpha > 16).astype(np.uint8)
    foreground_count = max(1, int(foreground.sum()))
    transparent_count = int((alpha < 5).sum())
    # Morphological closing using Pillow keeps this quality gate self-contained:
    # no OpenCV installation is required for the skill to run.
    closed_image = Image.fromarray(foreground * 255).filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.MinFilter(15))
    closed = (np.asarray(closed_image) > 0).astype(np.uint8)
    holes = (closed > 0) & (alpha < 5)
    weak_interior = (closed > 0) & (alpha < 80)
    hole_count = int(holes.sum())
    weak_count = int(weak_interior.sum())
    reasons: list[str] = []
    if transparent_count < alpha.size // 20:
        reasons.append("no_transparent_background")
    # Small genuine gaps between drumsticks, guitar strings and legs are not
    # missing subject pixels. Keep the floor high enough to allow those details,
    # while still rejecting the much larger holes from failed white-background
    # extraction.
    if hole_count > max(8000, foreground_count // 100):
        reasons.append("internal_transparent_holes")
    if weak_count > max(8000, foreground_count // 300):
        reasons.append("weak_alpha_inside_subject")
    return ("FAIL" if reasons else "PASS", hole_count, weak_count, transparent_count, tuple(reasons))


def inspect_rgba(rgba: np.ndarray) -> tuple[str, int, int, int, int, tuple[str, ...]]:
    """Inspect alpha defects and a likely white-background fringe on soft edges."""
    alpha = rgba[:, :, 3]
    status, holes, weak, transparent, reasons = inspect_alpha(alpha)
    foreground_count = max(1, int((alpha > 16).sum()))
    edge = (alpha >= 8) & (alpha <= 245)
    # A near-white pixel in a partially transparent edge is usually old white
    # studio background. It becomes a visible glow when composited on dark art.
    light_edge = edge & (rgba[:, :, :3].min(axis=2) >= 225)
    light_edge_count = int(light_edge.sum())
    updated_reasons = list(reasons)
    if light_edge_count > max(3000, foreground_count // 125):
        updated_reasons.append("light_edge_halo")
    return ("FAIL" if updated_reasons else status, holes, weak, transparent, light_edge_count, tuple(updated_reasons))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=True)
    options = parser.parse_args()
    image = Image.open(options.input).convert("RGBA")
    rgba = np.asarray(image)
    status, hole_count, weak_count, transparent_count, light_edge_count, reasons = inspect_rgba(rgba)

    panels = []
    for color, title in [((128, 128, 128, 255), "grey"), ((17, 24, 39, 255), "dark"), ((168, 50, 119, 255), "colour")]:
        panel = Image.new("RGBA", image.size, color)
        panel.alpha_composite(image)
        panels.append(panel)
    canvas = Image.new("RGB", (image.width * 3, image.height + 32), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (panel, title) in enumerate(zip(panels, ("grey", "dark", "colour"))):
        canvas.paste(panel.convert("RGB"), (index * image.width, 32))
        draw.text((index * image.width + 8, 8), title, fill="black")
    options.preview.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(options.preview, "JPEG", quality=94)
    print(f"status={status}")
    print(f"internal_hole_pixels={hole_count}")
    print(f"weak_interior_pixels={weak_count}")
    print(f"light_edge_halo_pixels={light_edge_count}")
    print(f"transparent_background_pixels={transparent_count}")
    print(f"reasons={','.join(reasons) if reasons else 'none'}")
    print(f"preview={options.preview}")
    if status == "FAIL":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
