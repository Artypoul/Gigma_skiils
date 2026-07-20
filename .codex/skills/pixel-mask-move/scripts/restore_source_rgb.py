#!/usr/bin/env python3
"""Restore exact source RGB under a cutout alpha without changing its mask."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Untouched flat RGB source")
    parser.add_argument("--cutout", type=Path, required=True, help="RGBA cutout whose alpha will be retained")
    parser.add_argument("--output", type=Path, required=True, help="New RGBA PNG")
    parser.add_argument("--force", action="store_true", help="Permit replacing an existing output")
    options = parser.parse_args()
    if options.output.exists() and not options.force:
        raise FileExistsError(f"Output already exists: {options.output}. Choose another name or use --force.")

    source = np.asarray(Image.open(options.source).convert("RGB"))
    cutout = np.asarray(Image.open(options.cutout).convert("RGBA")).copy()
    if source.shape[:2] != cutout.shape[:2]:
        raise ValueError("Source and cutout dimensions must exactly match.")
    visible = cutout[:, :, 3] > 0
    cutout[visible, :3] = source[visible]
    options.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(cutout, "RGBA").save(options.output, "PNG", optimize=True)
    print(f"output={options.output}")
    print(f"visible_source_rgb_restored={int(visible.sum())}")
    print("generation=none; alpha_changed=none")


if __name__ == "__main__":
    main()
