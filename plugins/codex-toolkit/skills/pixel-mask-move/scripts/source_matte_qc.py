#!/usr/bin/env python3
"""Detect likely source-background remnants inside a proposed RGBA matte.

This script never edits the image.  It is deliberately conservative: a white
shirt can look like a white studio background, so it reports candidates for
human review instead of deleting them by colour.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def load_rgb(path: str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def load_rgba(path: str) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)


def estimate_corner_background(rgb: np.ndarray) -> np.ndarray:
    """Estimate studio background only from four image corners."""
    height, width = rgb.shape[:2]
    border_y = max(8, height // 20)
    border_x = max(8, width // 20)
    samples = np.concatenate(
        (
            rgb[:border_y, :border_x].reshape(-1, 3),
            rgb[:border_y, width - border_x :].reshape(-1, 3),
            rgb[height - border_y :, :border_x].reshape(-1, 3),
            rgb[height - border_y :, width - border_x :].reshape(-1, 3),
        ),
        axis=0,
    )
    return np.median(samples, axis=0).astype(np.uint8)


def silhouette_edge(solid: np.ndarray) -> np.ndarray:
    image = Image.fromarray((solid * 255).astype(np.uint8), mode="L")
    eroded = np.asarray(image.filter(ImageFilter.MinFilter(3)), dtype=np.uint8) > 0
    return solid & ~eroded


def connected_to_edge(candidate: np.ndarray, edge: np.ndarray) -> np.ndarray:
    """Return candidate pixels connected to the silhouette edge (4-neighbour)."""
    height, width = candidate.shape
    visited = np.zeros_like(candidate, dtype=bool)
    seeds = np.argwhere(candidate & edge)
    queue: deque[tuple[int, int]] = deque((int(y), int(x)) for y, x in seeds)
    for y, x in queue:
        visited[y, x] = True
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < height and 0 <= nx < width and candidate[ny, nx] and not visited[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))
    return visited


def composite(rgba: np.ndarray, background: tuple[int, int, int]) -> np.ndarray:
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    bg = np.full_like(rgba[:, :, :3], background, dtype=np.float32)
    return np.clip(rgba[:, :, :3] * alpha + bg * (1.0 - alpha), 0, 255).astype(np.uint8)


def main() -> int:
    parser = argparse.ArgumentParser(description="Flag likely original-background remnants in an RGBA cutout.")
    parser.add_argument("--source", required=True, help="Untouched flat source image")
    parser.add_argument("--cutout", required=True, help="Proposed RGBA cutout aligned with source")
    parser.add_argument("--preview", required=True, help="Output preview PNG")
    parser.add_argument("--tolerance", type=float, default=18.0, help="RGB distance from estimated background")
    parser.add_argument("--reviewed-foreground", help="Optional hand-reviewed L mask of legitimate light foreground")
    args = parser.parse_args()

    source = load_rgb(args.source)
    cutout = load_rgba(args.cutout)
    if source.shape[:2] != cutout.shape[:2]:
        raise SystemExit("FAIL: source and cutout dimensions must match exactly")

    background = estimate_corner_background(source)
    alpha = cutout[:, :, 3]
    solid = alpha >= 250
    distance = np.linalg.norm(source.astype(np.int16) - background.astype(np.int16), axis=2)
    near_source_background = distance <= args.tolerance
    edge = silhouette_edge(solid)
    candidates = solid & near_source_background
    edge_connected = connected_to_edge(candidates, edge)
    enclosed = candidates & ~edge_connected

    # A one-pixel speck is noise; any larger interior region needs human review.
    reviewed = np.zeros_like(solid, dtype=bool)
    if args.reviewed_foreground:
        review = np.asarray(Image.open(args.reviewed_foreground).convert("L"), dtype=np.uint8)
        if review.shape != solid.shape:
            raise SystemExit("FAIL: reviewed foreground mask must match source dimensions")
        reviewed = review >= 128
    suspicious = enclosed & ~reviewed
    suspicious_count = int(suspicious.sum())
    candidate_count = int(candidates.sum())
    ys, xs = np.where(suspicious)
    bbox = "none" if suspicious_count == 0 else f"x={xs.min()}..{xs.max()}, y={ys.min()}..{ys.max()}"

    dark = composite(cutout, (20, 20, 24))
    magenta = composite(cutout, (210, 0, 150))
    marked = source.copy()
    marked[suspicious] = np.array([255, 0, 0], dtype=np.uint8)
    preview = np.concatenate((dark, magenta, marked), axis=1)
    Image.fromarray(preview, mode="RGB").save(args.preview)

    print(f"estimated_background_rgb={tuple(int(v) for v in background)}")
    print(f"near_background_solid_pixels={candidate_count}")
    print(f"interior_background_candidates={suspicious_count}")
    print(f"candidate_bbox={bbox}")
    print(f"preview={Path(args.preview)}")
    if suspicious_count:
        print("status=FAIL: inspect red pixels; they may be residual background or legitimate light clothing")
        return 2
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
