#!/usr/bin/env python3
"""Extract a structural inventory from a local Markdown/text prompt file."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(?:.*)$")
DEFAULT_MAX_BYTES = 2_000_000


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def read_text(path: Path, max_bytes: int) -> tuple[str, bytes]:
    if urlparse(str(path)).scheme in {"http", "https"}:
        fail("URLs are not supported; provide an explicit local file path")
    if not path.exists():
        fail(f"file does not exist: {path}")
    if not path.is_file():
        fail(f"path is not a file: {path}")
    try:
        with path.open("rb") as source:
            data = source.read(max_bytes + 1)
    except OSError as exc:
        fail(f"could not read file: {exc}")
    if len(data) > max_bytes:
        fail(f"file is too large: exceeds --max-bytes {max_bytes}")
    if b"\x00" in data:
        fail("file appears to be binary")
    try:
        return data.decode("utf-8-sig"), data
    except UnicodeDecodeError as exc:
        fail(f"file is not valid UTF-8 text: {exc}")


def collect_sections(text: str) -> list[dict[str, object]]:
    lines = text.splitlines()
    headings: list[dict[str, object]] = []
    fence: tuple[str, int] | None = None
    for index, line in enumerate(lines, start=1):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = (marker[0], len(marker))
            elif marker[0] == fence[0] and len(marker) >= fence[1]:
                fence = None
            continue
        if fence is not None:
            continue
        match = HEADING_RE.match(line)
        if not match:
            continue
        headings.append(
            {
                "level": len(match.group(1)),
                "title": match.group(2).strip(),
                "start_line": index,
            }
        )

    for index, heading in enumerate(headings):
        next_line = len(lines) + 1
        for later in headings[index + 1 :]:
            if int(later["level"]) <= int(heading["level"]):
                next_line = int(later["start_line"])
                break
        start_line = int(heading["start_line"])
        end_line = next_line - 1
        body = "\n".join(lines[start_line:end_line])
        heading["end_line"] = end_line
        heading["line_count"] = max(0, end_line - start_line)
        heading["char_count"] = len(body)
    return headings


def inventory(path: Path, text: str, data: bytes) -> dict[str, object]:
    lines = text.splitlines()
    return {
        "source": path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "lines": len(lines),
        "characters": len(text),
        "heading_count": len(collect_sections(text)),
        "sections": collect_sections(text),
    }


def render_markdown(result: dict[str, object]) -> str:
    rows = [
        "# Prompt Section Inventory",
        "",
        f"- Source: `{result['source']}`",
        f"- SHA-256: `{result['sha256']}`",
        f"- Bytes: {result['bytes']}",
        f"- Lines: {result['lines']}",
        f"- Characters: {result['characters']}",
        f"- Headings: {result['heading_count']}",
        "",
        "| Level | Title | Lines | Body lines | Body chars |",
        "| --- | --- | --- | --- | --- |",
    ]
    for section in result["sections"]:
        title = str(section["title"]).replace("|", "\\|")
        rows.append(
            "| {level} | {title} | {start}-{end} | {line_count} | {char_count} |".format(
                level=section["level"],
                title=title,
                start=section["start_line"],
                end=section["end_line"],
                line_count=section["line_count"],
                char_count=section["char_count"],
            )
        )
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit structural metadata for a local prompt file without executing or modifying it."
    )
    parser.add_argument("path", help="Local Markdown/text prompt file to inspect")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="Output format",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"Maximum file size to read, default {DEFAULT_MAX_BYTES}",
    )
    args = parser.parse_args()

    if args.max_bytes < 1:
        fail("--max-bytes must be positive")
    path = Path(args.path)
    text, data = read_text(path, args.max_bytes)
    result = inventory(path, text, data)

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
