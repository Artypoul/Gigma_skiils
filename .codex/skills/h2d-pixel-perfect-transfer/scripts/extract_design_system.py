#!/usr/bin/env python3
"""Extract the donor's design system from the decoded .h2d: tokens, containers, layouts, components.

A transfer that copies boxes one by one produces a page of hand-fitted blocks.
The donor was built the other way around — from a palette, a type scale, a
spacing scale, shared containers and repeated components — and this script
makes that system explicit so the candidate can be built from the same
building blocks and the gates can check reuse instead of coincidence.

  python scripts/extract_design_system.py \
    --decoded h2d-transfer-output/source/h2d_decoded.json \
    --out h2d-transfer-output/reports/design_system.json

Sections of the report:
  tokens.colors / typography / spacing / radii / shadows — recurring values
    with usage counts, ready to become CSS custom properties or a Tailwind
    theme instead of literals scattered per block;
  containers — per viewport, the shared content widths that section wrappers
    agree on (the donor's container chain);
  layouts — recurring flex/grid mechanisms (display + direction + alignment);
  components — repeated subtrees (cards, menu items, social links): same
    normalized signature appearing N times means one component in the
    candidate, never N pasted copies.
"""
from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TRANSPARENT = {"rgba(0, 0, 0, 0)", "transparent", ""}
# Generated-class suffixes: Header_Header__x7Kf2, css-1a2b3c, sc-gsTCUz. A BEM
# element (`card__title`) uses the same separator, so a suffix only counts as a
# hash when it looks generated — contains a digit or mixed case — never when it
# is a plain lowercase word.
_HASH_TAIL = re.compile(r"__(?=[A-Za-z0-9_-]*\d|[A-Za-z0-9_-]*[A-Z])[A-Za-z0-9_-]{4,}$")
_HASH_CLASS = re.compile(r"^(css|sc)-[A-Za-z0-9]+$")


def norm_class(name: str) -> str | None:
    if _HASH_CLASS.match(name):
        return None
    return _HASH_TAIL.sub("", name)


def norm_classes(node: dict[str, Any]) -> tuple[str, ...]:
    raw = node.get("classList")
    if not isinstance(raw, list):
        return ()
    out = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            normalized = norm_class(item.strip())
            if normalized:
                out.append(normalized)
    return tuple(sorted(set(out)))


def styles_of(node: dict[str, Any]) -> dict[str, Any]:
    styles = node.get("styles")
    return styles if isinstance(styles, dict) else {}


def walk(node: Any, h2d_path: str, viewport: int | None):
    if not isinstance(node, dict):
        return
    yield node, h2d_path, viewport
    children = node.get("children")
    if isinstance(children, list):
        for i, child in enumerate(children):
            yield from walk(child, f"{h2d_path}.{i}", viewport)


def viewport_of(branch: dict[str, Any]) -> int | None:
    for key in ("width", "innerWidth"):
        value = branch.get(key)
        if isinstance(value, (int, float)):
            return int(round(value))
    doc = branch.get("doc")
    if isinstance(doc, dict):
        for key in ("innerWidth", "width"):
            value = doc.get(key)
            if isinstance(value, (int, float)):
                return int(round(value))
    return None


def branch_viewport(branch: dict[str, Any], frame: dict[str, Any]) -> int | None:
    """Branch metadata first; the frame's own width is the honest fallback."""
    viewport = viewport_of(branch)
    if viewport:
        return viewport
    width = frame.get("width")
    if isinstance(width, (int, float)) and width > 0:
        return int(round(width))
    return None


def roots_of(decoded: Any):
    # Shapes mirror h2d_unpack_source.build_tree_index: a dict with
    # frame/alternatives, or a top-level list of branches.
    if isinstance(decoded, dict):
        if isinstance(decoded.get("frame"), dict):
            yield decoded["frame"], "0", branch_viewport(decoded, decoded["frame"])
        for i, alt in enumerate(decoded.get("alternatives") or []):
            if isinstance(alt, dict) and isinstance(alt.get("frame"), dict):
                yield alt["frame"], f"alt{i}:0", branch_viewport(alt, alt["frame"])
    elif isinstance(decoded, list):
        for i, item in enumerate(decoded):
            if isinstance(item, dict):
                frame = item.get("frame") if isinstance(item.get("frame"), dict) else item
                yield frame, f"{i}.0", branch_viewport(item, frame)


def top(counter: Counter, limit: int) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


PX_PART = re.compile(r"-?\d+(?:\.\d+)?px")


def spacing_parts(value: Any) -> list[str]:
    return [part for part in PX_PART.findall(str(value)) if part not in ("0px", "-0px")]


def collect_tokens(nodes: list[tuple[dict[str, Any], str, int | None]], limit: int) -> dict[str, Any]:
    colors: Counter = Counter()
    color_usage: dict[str, set[str]] = defaultdict(set)
    typography: Counter = Counter()
    spacing: Counter = Counter()
    radii: Counter = Counter()
    shadows: Counter = Counter()
    for node, _, _ in nodes:
        styles = styles_of(node)
        if not styles:
            continue
        for prop in ("color", "backgroundColor", "borderColor", "fill"):
            value = str(styles.get(prop) or "").strip()
            if value and value not in TRANSPARENT:
                colors[value] += 1
                color_usage[value].add(prop)
        family = styles.get("fontFamily")
        size = styles.get("fontSize")
        # Zero-size text is a hidden/measuring node, not a type-scale member.
        if family and size and str(size) not in ("0px", "0"):
            key = json.dumps({
                "fontFamily": family, "fontSize": size,
                "fontWeight": styles.get("fontWeight") or "400",
                "lineHeight": styles.get("lineHeight") or "normal",
            }, sort_keys=True)
            typography[key] += 1
        for prop in ("padding", "margin", "gap"):
            for part in spacing_parts(styles.get(prop)):
                spacing[part] += 1
        for prop in ("borderTopLeftRadius", "borderTopRightRadius", "borderBottomLeftRadius", "borderBottomRightRadius"):
            value = str(styles.get(prop) or "").strip()
            if value and value not in ("0px", ""):
                radii[value] += 1
        shadow = str(styles.get("boxShadow") or "").strip()
        if shadow and shadow != "none":
            shadows[shadow] += 1
    return {
        "colors": [
            {"value": value, "count": count, "usage": sorted(color_usage[value])}
            for value, count in colors.most_common(limit)
        ],
        "typography": [
            {**json.loads(key), "count": count}
            for key, count in typography.most_common(limit)
        ],
        "spacing": top(spacing, limit),
        "radii": top(radii, limit),
        "shadows": top(shadows, limit),
    }


def collect_containers(per_viewport: dict[int, list[tuple[dict[str, Any], str]]], limit: int) -> list[dict[str, Any]]:
    """Shared content widths per viewport — the donor's container chain.

    A width is a container signal when several distinct wrappers agree on it
    exactly and it is narrower than the viewport itself.
    """
    out = []
    for viewport, entries in sorted(per_viewport.items(), reverse=True):
        widths: Counter = Counter()
        samples: dict[str, list[str]] = defaultdict(list)
        for node, h2d_path in entries:
            width = node.get("width")
            # Content containers live in the hundreds of pixels; recurring small
            # widths are icons and controls, not the container chain.
            if not isinstance(width, (int, float)) or not viewport or not (200 <= width < viewport):
                continue
            children = node.get("children")
            if not isinstance(children, list) or not children:
                continue
            key = f"{round(float(width), 1):g}px"
            widths[key] += 1
            if len(samples[key]) < 5:
                samples[key].append(h2d_path)
        shared = [
            {"width": value, "count": count, "sample_paths": samples[value]}
            for value, count in widths.most_common(limit)
            if count >= 3
        ]
        out.append({"viewport": viewport, "shared_widths": shared})
    return out


def collect_layouts(nodes: list[tuple[dict[str, Any], str, int | None]], limit: int) -> list[dict[str, Any]]:
    layouts: Counter = Counter()
    samples: dict[str, list[str]] = defaultdict(list)
    for node, h2d_path, _ in nodes:
        styles = styles_of(node)
        display = str(styles.get("display") or "").strip()
        if display not in ("flex", "inline-flex", "grid", "inline-grid"):
            continue
        parts = [display]
        for prop in ("flexDirection", "justifyContent", "alignItems", "flexWrap"):
            value = str(styles.get(prop) or "").strip()
            if value and value not in ("normal", "stretch", "nowrap"):
                parts.append(f"{prop}:{value}")
        gap = str(styles.get("gap") or "").strip()
        if gap and gap not in ("0px", "normal"):
            parts.append(f"gap:{gap}")
        grid = str(styles.get("gridTemplateColumns") or "").strip()
        if grid and grid != "none":
            parts.append(f"columns:{len(grid.split())}")
        key = " ".join(parts)
        layouts[key] += 1
        if len(samples[key]) < 5:
            samples[key].append(h2d_path)
    return [
        {"signature": key, "count": count, "sample_paths": samples[key]}
        for key, count in layouts.most_common(limit)
    ]


def node_signature(node: dict[str, Any], depth: int = 2) -> str | None:
    """Structural identity of a subtree: tag + normalized classes + children shape."""
    tag = node.get("tag")
    if not isinstance(tag, str) or not tag:
        return None
    classes = norm_classes(node)
    parts = [tag + ("." + ".".join(classes) if classes else "")]
    if depth > 0:
        child_parts = []
        for child in (node.get("children") or []):
            if isinstance(child, dict):
                child_signature = node_signature(child, depth - 1)
                if child_signature:
                    child_parts.append(child_signature)
        if child_parts:
            parts.append("[" + ",".join(child_parts) + "]")
    return "".join(parts)


def collect_components(per_viewport: dict[int, list[tuple[dict[str, Any], str]]], limit: int, min_repeats: int) -> list[dict[str, Any]]:
    """Repeated subtrees = component candidates.

    Grouping runs per viewport so a card repeated across breakpoints does not
    fake a higher count; the report keeps the viewport with the most repeats.
    """
    best: dict[str, dict[str, Any]] = {}
    for viewport, entries in per_viewport.items():
        groups: dict[str, list[str]] = defaultdict(list)
        for node, h2d_path in entries:
            children = node.get("children")
            has_children = isinstance(children, list) and children
            if not has_children and not norm_classes(node):
                continue
            signature = node_signature(node)
            if signature and len(signature) > 8:
                groups[signature].append(h2d_path)
        for signature, paths in groups.items():
            if len(paths) < min_repeats:
                continue
            # Nested repetition inflates counts: keep only the outermost instances.
            outer = [p for p in paths if not any(p != q and p.startswith(q + ".") for q in paths)]
            if len(outer) < min_repeats:
                continue
            current = best.get(signature)
            if current is None or len(outer) > current["count"]:
                best[signature] = {
                    "signature": signature[:240],
                    "count": len(outer),
                    "viewport": viewport,
                    "sample_paths": outer[:5],
                }
    ranked = sorted(best.values(), key=lambda item: item["count"], reverse=True)
    return ranked[:limit]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--decoded", type=Path, required=True, help="source/h2d_decoded.json from the unpack step")
    ap.add_argument("--top", type=int, default=24, help="Max entries per token/layout table")
    ap.add_argument("--min-component-repeats", type=int, default=3)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    decoded = json.loads(args.decoded.read_text(encoding="utf-8"))
    all_nodes: list[tuple[dict[str, Any], str, int | None]] = []
    per_viewport: dict[int, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    skipped_branches: list[str] = []
    for root, prefix, viewport in roots_of(decoded):
        for node, h2d_path, vp in walk(root, prefix, viewport):
            all_nodes.append((node, h2d_path, vp))
            if vp:
                per_viewport[vp].append((node, h2d_path))
        if not viewport:
            skipped_branches.append(prefix)

    styled = sum(1 for node, _, _ in all_nodes if styles_of(node))
    tokens = collect_tokens(all_nodes, args.top)
    issues = []
    if not styled:
        issues.append("decoded tree carries no styles: re-run h2d_unpack_source.py from this skill version")
    for prefix in skipped_branches:
        # Tokens and layouts still cover these nodes; only the per-viewport
        # container/component analysis cannot place them. Saying so beats
        # silently reporting an emptier system than the donor has.
        issues.append(f"branch {prefix} has no viewport metadata and no frame width; excluded from containers/components")
    report = {
        "result": "pass" if styled and tokens["colors"] and tokens["typography"] and not skipped_branches else "needs-fix",
        "viewports": sorted(per_viewport, reverse=True),
        "nodes_seen": len(all_nodes),
        "nodes_with_styles": styled,
        "tokens": tokens,
        "containers": collect_containers(per_viewport, args.top),
        "layouts": collect_layouts(all_nodes, args.top),
        "components": collect_components(per_viewport, args.top, args.min_component_repeats),
        "issues": issues,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"result={report['result']} colors={len(tokens['colors'])} typography={len(tokens['typography'])} "
        f"spacing={len(tokens['spacing'])} layouts={len(report['layouts'])} components={len(report['components'])} out={args.out}"
    )
    return 0 if report["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
