#!/usr/bin/env python3
"""Dependency-free bounds checks for exact pixel translations."""

from __future__ import annotations


def ensure_translation_fits(
    *,
    bounds: tuple[int, int, int, int],
    canvas_size: tuple[int, int],
    dx: int,
    dy: int,
) -> None:
    """Reject a translation that would clip any visible selected pixel."""
    left, top, right, bottom = bounds
    width, height = canvas_size
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError("Visible selection bounds must be inside the canvas.")
    moved = (left + dx, top + dy, right + dx, bottom + dy)
    if moved[0] < 0 or moved[1] < 0 or moved[2] > width or moved[3] > height:
        raise ValueError(
            "Offset would clip visible selected pixels outside the canvas; "
            "reduce the shift or enlarge the canvas."
        )
