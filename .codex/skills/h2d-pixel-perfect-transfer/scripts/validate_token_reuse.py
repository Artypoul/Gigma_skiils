#!/usr/bin/env python3
"""Candidate-side token gate: the donor's palette lives in one token layer, not in scattered literals.

`design_system.json` describes the donor. This gate reads the CANDIDATE's
sources: every significant donor color must come from a shared token layer
(CSS custom properties, a theme file, a Tailwind config), and hardcoding the
same literal block after block is exactly the failure being rejected. Color is
the gated token class because a palette literal is unambiguous in source code;
spacing values like `12px` appear for too many unrelated reasons to grep for.

  python scripts/validate_token_reuse.py \
    --design-system h2d-transfer-output/reports/design_system.json \
    --candidate-root . \
    --token-file src/styles/tokens.css \
    --out h2d-transfer-output/reports/token_reuse.json

Rules:
  - a donor color with fewer donor usages than --min-donor-count is ignored;
  - occurrences inside token files (named like tokens/theme/variables/palette,
    a tailwind config, or passed via --token-file) are the shared layer;
  - up to --max-scatter literal occurrences outside the token layer are
    tolerated (one-off utilities); more is a scattered palette and fails.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any

SOURCE_EXTENSIONS = {".css", ".scss", ".less", ".styl", ".svelte", ".vue", ".jsx", ".tsx", ".js", ".ts", ".html"}
EXCLUDED_DIRS = {"node_modules", "dist", "build", "build-ssr", "vendor", "output", ".git", ".artifacts", ".svelte-kit", ".next", "coverage"}
TOKEN_FILE_HINTS = ("token", "theme", "variables", "palette", "tailwind.config")

RGB_PATTERN = re.compile(r"^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([0-9.]+))?\)$")


def color_needles(value: str) -> list[str] | None:
    """Every spelling of the donor color worth grepping for, lowercase."""
    match = RGB_PATTERN.match(value.strip())
    if not match:
        return None
    r, g, b = (int(match.group(i)) for i in (1, 2, 3))
    alpha = match.group(4)
    if alpha is not None:
        # Alpha colors are matched textually; 8-digit hex is too rare to chase.
        spaced = f"rgba({r}, {g}, {b}, {alpha})"
        return [spaced, spaced.replace(", ", ",")]
    hex_full = f"#{r:02x}{g:02x}{b:02x}"
    needles = [f"rgb({r}, {g}, {b})", f"rgb({r},{g},{b})", f"rgba({r}, {g}, {b},", f"rgba({r},{g},{b},", hex_full]
    if hex_full[1] == hex_full[2] and hex_full[3] == hex_full[4] and hex_full[5] == hex_full[6]:
        needles.append(f"#{hex_full[1]}{hex_full[3]}{hex_full[5]}")
    return needles


def is_token_file(path: Path, explicit: set[Path]) -> bool:
    if path in explicit:
        return True
    name = path.name.lower()
    return any(hint in name for hint in TOKEN_FILE_HINTS)


def iter_sources(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        out.append(path)
    return out


def count_occurrences(text: str, needles: list[str]) -> int:
    # The full rgb()/hex spellings do not overlap, so a plain sum is exact.
    return sum(text.count(needle) for needle in needles)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--design-system", type=Path, required=True)
    ap.add_argument("--candidate-root", type=Path, required=True)
    ap.add_argument("--token-file", action="append", type=Path, default=[], help="File(s) where palette literals legitimately live; repeatable")
    ap.add_argument("--min-donor-count", type=int, default=10, help="Ignore donor colors used fewer times than this")
    ap.add_argument("--max-scatter", type=int, default=3, help="Tolerated literal occurrences outside the token layer per color")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    design = json.loads(args.design_system.read_text(encoding="utf-8"))
    root = args.candidate_root.resolve()
    explicit_tokens = {(root / p).resolve() if not p.is_absolute() else p.resolve() for p in args.token_file}
    for path in explicit_tokens:
        try:
            path.relative_to(root)
        except ValueError:
            raise SystemExit(f"--token-file must live inside the candidate root: {path}")

    palette = [c for c in (design.get("tokens", {}).get("colors") or []) if (c.get("count") or 0) >= args.min_donor_count]
    sources = iter_sources(root)
    token_files = [p for p in sources if is_token_file(p, explicit_tokens)]
    other_files = [p for p in sources if not is_token_file(p, explicit_tokens)]
    texts = {p: p.read_text(encoding="utf-8", errors="replace").lower() for p in sources}

    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for color in palette:
        needles = color_needles(str(color.get("value", "")))
        if not needles:
            continue
        needles = [n.lower() for n in needles]
        token_count = sum(count_occurrences(texts[p], needles) for p in token_files)
        scattered: list[str] = []
        scatter_count = 0
        for path in other_files:
            found = count_occurrences(texts[path], needles)
            if found:
                scatter_count += found
                if len(scattered) < 5:
                    scattered.append(f"{path.relative_to(root).as_posix()} (x{found})")
        entry: dict[str, Any] = {
            "color": color["value"],
            "donor_count": color.get("count"),
            "token_layer_occurrences": token_count,
            "scattered_occurrences": scatter_count,
        }
        if scatter_count > args.max_scatter:
            entry["result"] = "fail"
            entry["scattered_in"] = scattered
            detail = "no token layer defines it" if token_count == 0 else "a token exists but blocks keep hardcoding the literal"
            issues.append({"color": color["value"], "issue": f"palette literal appears {scatter_count} times outside the token layer ({detail}); route it through one shared token", "files": scattered})
        else:
            entry["result"] = "pass"
        checks.append(entry)

    if not palette:
        result = "no-donor-palette"
    elif issues:
        result = "fail"
    else:
        result = "pass"
    report = {
        "result": result,
        "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "min_donor_count": args.min_donor_count,
        "max_scatter": args.max_scatter,
        "sources_scanned": len(sources),
        "token_files": [p.relative_to(root).as_posix() for p in token_files],
        "checks": checks,
        "issues": issues,
    }
    if not token_files and palette:
        report["issues"].append({"issue": "no token layer found (no --token-file and no tokens/theme/variables/palette/tailwind.config source); the palette has nowhere shared to live"})
        report["result"] = "fail"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"result={report['result']} colors_checked={len(checks)} sources={len(sources)} token_files={len(token_files)} issues={len(report['issues'])} out={args.out}")
    return 0 if report["result"] in ("pass", "no-donor-palette") else 2


if __name__ == "__main__":
    raise SystemExit(main())
