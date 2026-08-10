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
    --token-map h2d-transfer-output/contract/token_map.json \
    --out h2d-transfer-output/reports/token_reuse.json

The repeat floor and literal-scatter allowance are bundled invariants, not CLI
knobs. Each significant donor color must be mapped to one definition and one
usage spelling. The definition must contain the donor literal and token name;
the usage must appear outside the definition; repeated literals outside the
definition fail.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any

SOURCE_EXTENSIONS = {".css", ".scss", ".less", ".styl", ".svelte", ".vue", ".jsx", ".tsx", ".js", ".ts", ".html"}
EXCLUDED_DIRS = {"node_modules", "dist", "build", "build-ssr", "vendor", "output", ".git", ".artifacts", ".svelte-kit", ".next", "coverage"}
MIN_DONOR_COUNT = 3
MAX_SCATTER = 1

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
    ap.add_argument("--token-map", type=Path, required=True, help="Pinned donor-color to candidate-token declaration")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    design = json.loads(args.design_system.read_text(encoding="utf-8"))
    token_map = json.loads(args.token_map.read_text(encoding="utf-8"))
    root = args.candidate_root.resolve()
    mappings = token_map.get("colors") if isinstance(token_map, dict) else None
    if not isinstance(mappings, dict):
        raise SystemExit("--token-map must contain a colors object")

    palette = [c for c in (design.get("tokens", {}).get("colors") or []) if (c.get("count") or 0) >= MIN_DONOR_COUNT]
    sources = iter_sources(root)
    texts = {p: p.read_text(encoding="utf-8", errors="replace").lower() for p in sources}
    token_files: set[Path] = set()

    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for color in palette:
        needles = color_needles(str(color.get("value", "")))
        if not needles:
            continue
        needles = [n.lower() for n in needles]
        value = str(color.get("value", ""))
        mapping = mappings.get(value)
        entry: dict[str, Any] = {"color": value, "donor_count": color.get("count")}
        if not isinstance(mapping, dict):
            entry["result"] = "fail"
            checks.append(entry)
            issues.append({"color": value, "issue": "significant donor color is missing from the pinned token map"})
            continue
        definition_value = mapping.get("definition")
        token_name = mapping.get("token")
        usage = mapping.get("usage")
        if not all(isinstance(item, str) and item.strip() for item in (definition_value, token_name, usage)):
            entry["result"] = "fail"
            checks.append(entry)
            issues.append({"color": value, "issue": "token map entry needs non-empty definition, token and usage strings"})
            continue
        definition = (root / definition_value).resolve()
        try:
            definition.relative_to(root)
        except ValueError:
            entry["result"] = "fail"
            checks.append(entry)
            issues.append({"color": value, "issue": f"token definition escapes candidate root: {definition_value}"})
            continue
        if definition not in texts:
            entry["result"] = "fail"
            checks.append(entry)
            issues.append({"color": value, "issue": f"token definition is missing or not a source file: {definition_value}"})
            continue
        token_files.add(definition)
        definition_text = texts[definition]
        literal_in_definition = count_occurrences(definition_text, needles)
        token_in_definition = definition_text.count(token_name.lower())
        usage_count = sum(text.count(usage.lower()) for path, text in texts.items() if path != definition)
        scattered: list[str] = []
        scatter_count = 0
        for path in sources:
            if path == definition:
                continue
            found = count_occurrences(texts[path], needles)
            if found:
                scatter_count += found
                if len(scattered) < 5:
                    scattered.append(f"{path.relative_to(root).as_posix()} (x{found})")
        entry.update({
            "definition": Path(definition_value).as_posix(),
            "token": token_name,
            "usage": usage,
            "token_layer_occurrences": literal_in_definition,
            "candidate_token_usages": usage_count,
            "scattered_occurrences": scatter_count,
        })
        if literal_in_definition < 1 or token_in_definition < 1 or usage_count < 1:
            entry["result"] = "fail"
            issues.append({"color": value, "issue": "token definition must contain the donor literal and token name, and the declared usage must occur outside that definition"})
        elif scatter_count > MAX_SCATTER:
            entry["result"] = "fail"
            entry["scattered_in"] = scattered
            issues.append({"color": value, "issue": f"palette literal appears {scatter_count} times outside its token definition; route it through the shared token", "files": scattered})
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
        "token_map_sha256": hashlib.sha256(args.token_map.read_bytes()).hexdigest(),
        "min_donor_count": MIN_DONOR_COUNT,
        "max_scatter": MAX_SCATTER,
        "sources_scanned": len(sources),
        "token_files": sorted(p.relative_to(root).as_posix() for p in token_files),
        "checks": checks,
        "issues": issues,
    }
    if not token_files and palette:
        report["issues"].append({"issue": "no valid token definition from the pinned token map was found in the candidate"})
        report["result"] = "fail"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"result={report['result']} colors_checked={len(checks)} sources={len(sources)} token_files={len(token_files)} issues={len(report['issues'])} out={args.out}")
    return 0 if report["result"] in ("pass", "no-donor-palette") else 2


if __name__ == "__main__":
    raise SystemExit(main())
