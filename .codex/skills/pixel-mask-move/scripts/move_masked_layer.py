#!/usr/bin/env python3
"""Move a masked RGBA layer by an exact integer offset without resampling."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from alpha_qc import inspect_rgba


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="RGBA PNG source")
    parser.add_argument("--mask", type=Path, required=True, help="Hand-checked grayscale selection mask, same dimensions as input")
    parser.add_argument("--dx", required=True, type=int, help="Integer horizontal shift; negative moves left")
    parser.add_argument("--dy", default=0, type=int, help="Integer vertical shift; negative moves up")
    parser.add_argument("--output", required=True, type=Path, help="New PNG file; never use input path")
    parser.add_argument("--preview", type=Path, help="Optional checkerboard JPEG preview")
    parser.add_argument("--layer-order", choices=("front", "behind"), default="front", help="Stacking order when moved pixels overlap the base")
    parser.add_argument("--allow-overlap", action="store_true", help="Permit moved layer to appear in front of other pixels")
    parser.add_argument("--force", action="store_true", help="Permit replacing an existing output file")
    return parser.parse_args()


def translate(array: np.ndarray, dx: int, dy: int) -> np.ndarray:
    height, width = array.shape[:2]
    moved = np.zeros_like(array)
    src_x1, src_x2 = max(0, -dx), min(width, width - dx)
    src_y1, src_y2 = max(0, -dy), min(height, height - dy)
    if src_x1 >= src_x2 or src_y1 >= src_y2:
        raise ValueError("Offset moves the selected layer completely outside the canvas.")
    dst_x1, dst_x2 = src_x1 + dx, src_x2 + dx
    dst_y1, dst_y2 = src_y1 + dy, src_y2 + dy
    moved[dst_y1:dst_y2, dst_x1:dst_x2] = array[src_y1:src_y2, src_x1:src_x2]
    return moved


def checkerboard(size: tuple[int, int], tile: int = 24) -> Image.Image:
    canvas = Image.new("RGBA", size, (238, 238, 238, 255))
    draw = ImageDraw.Draw(canvas)
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=(202, 202, 202, 255))
    return canvas


def main() -> None:
    options = args()
    if options.output.resolve() == options.input.resolve():
        raise ValueError("--output must be a new filename; input is never overwritten.")
    if options.output.exists() and not options.force:
        raise FileExistsError(f"Output already exists: {options.output}. Choose another name or use --force.")

    source = Image.open(options.input).convert("RGBA")
    rgba = np.array(source)
    alpha = rgba[:, :, 3]
    qc_status, _, _, _, _, qc_reasons = inspect_rgba(rgba)
    if qc_status != "PASS":
        raise ValueError(
            "Input alpha failed the identity-lock quality gate: "
            f"{', '.join(qc_reasons)}. Supply a clean, verified RGBA cutout; do not use generation to repair it."
        )
    mask = np.array(Image.open(options.mask).convert("L"))
    if mask.shape != alpha.shape:
        raise ValueError("Mask dimensions must exactly match the input image.")

    # Preserve all selected source pixels, including their original soft alpha.
    selected_alpha = ((alpha.astype(np.uint16) * mask.astype(np.uint16)) // 255).astype(np.uint8)
    if not np.any(selected_alpha):
        raise ValueError("The mask selects no visible pixels.")
    layer = rgba.copy()
    layer[:, :, 3] = selected_alpha
    layer[selected_alpha == 0, :3] = 0

    # Remove selected pixels completely at their old position, then translate exactly.
    base = rgba.copy()
    base[:, :, 3] = ((alpha.astype(np.uint16) * (255 - mask.astype(np.uint16))) // 255).astype(np.uint8)
    base[base[:, :, 3] == 0, :3] = 0
    moved = translate(layer, options.dx, options.dy)

    overlap = (base[:, :, 3] > 16) & (moved[:, :, 3] > 16)
    overlap_count = int(overlap.sum())
    if overlap_count and options.layer_order == "front" and not options.allow_overlap:
        raise ValueError(
            f"Move would overlap {overlap_count} visible pixels. Refusing to hide or damage another person; "
            "reduce the shift, refine the mask, or explicitly use --allow-overlap."
        )

    if options.layer_order == "behind":
        output = Image.fromarray(moved, "RGBA")
        output.alpha_composite(Image.fromarray(base, "RGBA"))
    else:
        output = Image.fromarray(base, "RGBA")
        output.alpha_composite(Image.fromarray(moved, "RGBA"))
    output_rgba = np.array(output)
    # Outside both the old selection and its translated destination, a true pixel
    # move must leave every source pixel exactly unchanged.
    # Transparent pixels may carry arbitrary, invisible RGB values. Integrity is
    # defined only for visible source pixels outside the old/new selected layer.
    untouched = (mask == 0) & (moved[:, :, 3] == 0) & (alpha > 0)
    changed_untouched = int(np.any(output_rgba != rgba, axis=2)[untouched].sum())
    if changed_untouched:
        raise RuntimeError(f"Integrity check failed: {changed_untouched} unrelated pixels changed.")
    output_qc_status, _, _, _, _, output_qc_reasons = inspect_rgba(output_rgba)
    if output_qc_status != "PASS":
        raise RuntimeError(
            "Output alpha failed the identity-lock quality gate: "
            f"{', '.join(output_qc_reasons)}. No file was saved."
        )
    options.output.parent.mkdir(parents=True, exist_ok=True)
    output.save(options.output, "PNG", optimize=True)

    if options.preview:
        options.preview.parent.mkdir(parents=True, exist_ok=True)
        preview = checkerboard(source.size)
        preview.alpha_composite(output)
        preview.convert("RGB").save(options.preview, "JPEG", quality=96)

    print(f"input={options.input}")
    print(f"output={options.output}")
    print(f"offset=({options.dx}, {options.dy})")
    print(f"layer_order={options.layer_order}")
    print(f"overlap_pixels={overlap_count}")
    print(f"unrelated_pixels_changed={changed_untouched}")
    print("output_alpha_qc=PASS")
    print("pixel_editing=none; scale=1; generation=none")


if __name__ == "__main__":
    main()
