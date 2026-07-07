#!/usr/bin/env python3
"""H2D source unpack helper for h2d-pixel-perfect-transfer v1.5.

Creates a byte-identical source copy, decode/unpack reports, compact decoded JSON,
H2D tree index, schema discovery, and optional embedded asset extraction.

Observed for one html.to.design export:
    bytes -> XOR 0x39 -> raw deflate -> UTF-8 JSON
This is a candidate, not a universal rule.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import mimetypes
import re
import shutil
import zipfile
import zlib
from collections import Counter, deque
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import unquote_to_bytes

try:
    from PIL import Image, ImageChops
except Exception:
    Image = ImageChops = None

DATA_URI_RE = re.compile(r"^data:([^;,]+)?(;base64)?,(.*)$", re.DOTALL)
JSON_STARTS = (b"{", b"[")
RECT_KEYS = {"x", "y", "width", "height"}
NODE_TYPES = {"FRAME", "TEXT", "SVG", "IMAGE", "CANVAS", "GROUP", "INSTANCE", "VECTOR"}
DEFAULT_MAX_OUTPUT = 256 * 1024 * 1024


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: Any, *, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        if pretty:
            json.dump(value, f, ensure_ascii=False, indent=2)
        else:
            json.dump(value, f, ensure_ascii=False, separators=(",", ":"))


def stripped(data: bytes) -> bytes:
    return data.lstrip(b"\xef\xbb\xbf\x00\t\r\n ")


def sniff_kind(data: bytes) -> str:
    s = stripped(data)
    if s.startswith(JSON_STARTS):
        return "json"
    if zipfile.is_zipfile(io.BytesIO(data)):
        return "zip"
    if data.startswith(b"\x1f\x8b"):
        return "gzip"
    if data[:2] in {b"\x78\x01", b"\x78\x9c", b"\x78\xda"}:
        return "zlib"
    x39 = bytes(b ^ 0x39 for b in data[:8])
    if stripped(x39).startswith(JSON_STARTS) or x39[:2] in {b"\x78\x01", b"\x78\x9c", b"\x78\xda"}:
        return "xor-0x39-candidate"
    compact = b"".join(data[:4096].split())
    b64chars = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
    if len(compact) > 64 and all(c in b64chars for c in compact):
        return "base64-like"
    return "unknown"


def safe_zip_members(zip_path: Path, out_dir: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    extracted: list[Path] = []
    manifest: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts:
                manifest.append({"path": name, "status": "blocked", "reason": "unsafe path"})
                continue
            if info.is_dir():
                continue
            target = out_dir.joinpath(*pure.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(target)
            manifest.append({"path": name, "status": "extracted", "bytes": target.stat().st_size, "sha256": sha256_file(target)})
    return extracted, manifest


def parse_json_bytes(data: bytes) -> Any | None:
    if not stripped(data).startswith(JSON_STARTS):
        return None
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return json.loads(data.decode(enc))
        except Exception:
            pass
    return None


def decompress_variants(data: bytes, max_output: int) -> Iterable[tuple[str, int | None, bytes]]:
    yield "identity", None, data
    for name, wbits in (("zlib", zlib.MAX_WBITS), ("raw-deflate", -zlib.MAX_WBITS), ("gzip-or-zlib", 15 + 32)):
        try:
            dec = zlib.decompress(data, wbits)
            if len(dec) <= max_output:
                yield name, wbits, dec
        except Exception:
            pass


def shape_stats(obj: Any, max_visit: int = 150_000) -> dict[str, Any]:
    q: deque[Any] = deque([obj])
    visited = rect_like = text_like = asset_like = 0
    type_counts: Counter[str] = Counter()
    viewport_candidates: set[int] = set()
    while q and visited < max_visit:
        cur = q.popleft()
        visited += 1
        if isinstance(cur, dict):
            keys = set(cur.keys())
            if RECT_KEYS.issubset(keys):
                rect_like += 1
            typ = cur.get("type") or cur.get("nodeType") or cur.get("kind")
            if isinstance(typ, str):
                type_counts[typ] += 1
                if typ.upper() in NODE_TYPES:
                    rect_like += 1
                if typ.upper() == "TEXT":
                    text_like += 1
                if typ.upper() in {"SVG", "IMAGE", "CANVAS"}:
                    asset_like += 1
            for k in ("width", "innerWidth", "viewport", "screenWidth"):
                v = cur.get(k)
                if isinstance(v, (int, float)) and 250 <= int(v) <= 4000:
                    viewport_candidates.add(int(v))
            for v in cur.values():
                if isinstance(v, (dict, list)):
                    q.append(v)
                elif isinstance(v, str):
                    s = v.strip()[:200]
                    if s.startswith("<svg") or s.startswith("data:image/"):
                        asset_like += 1
                    if 0 < len(s) < 200 and any(ch.isalpha() for ch in s):
                        text_like += 1
        elif isinstance(cur, list):
            q.extend(v for v in cur if isinstance(v, (dict, list)))
    score = min(rect_like, 120) + min(text_like, 30) + min(asset_like, 30) + min(len(viewport_candidates) * 4, 40)
    for t in ("FRAME", "TEXT", "SVG", "IMAGE", "CANVAS"):
        if type_counts.get(t):
            score += 5
    return {
        "score": score,
        "visited": visited,
        "truncated": bool(q),
        "rect_like_count": rect_like,
        "text_like_count": text_like,
        "asset_like_count": asset_like,
        "viewport_candidates": sorted(viewport_candidates),
        "type_counts_sample": dict(type_counts.most_common(40)),
        "looks_like_h2d": score >= 20 and rect_like > 0,
    }


def decode_file_candidates(path: Path, brute_force_xor: bool, max_output: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw = path.read_bytes()
    transforms: list[tuple[str, int | None, bytes]] = [("raw", None, raw), ("xor-0x39", 0x39, bytes(b ^ 0x39 for b in raw))]
    if brute_force_xor and len(raw) <= 32 * 1024 * 1024:
        transforms.extend((f"xor-{k:#04x}", k, bytes(b ^ k for b in raw)) for k in range(256) if k != 0x39)
    public: list[dict[str, Any]] = []
    valid: list[dict[str, Any]] = []
    for transform, xor_key, payload in transforms:
        for codec, wbits, decoded in decompress_variants(payload, max_output):
            rec = {"source_file": str(path), "transform": transform, "xor_key": xor_key, "codec": codec, "wbits": wbits, "decoded_bytes": len(decoded)}
            obj = parse_json_bytes(decoded)
            if obj is None:
                rec.update({"status": "fail", "score": 0, "reason": "not utf8 json"})
                public.append(rec)
                continue
            stats = shape_stats(obj)
            rec.update({"status": "ok", "score": stats["score"], "shape": stats, "decoded_sha256": sha256_bytes(decoded)})
            public.append(rec)
            if stats["looks_like_h2d"]:
                valid.append({**rec, "json": obj, "decoded": decoded})
    # Optional one-level base64 wrapper.
    if sniff_kind(raw) == "base64-like":
        try:
            b64 = base64.b64decode(b"".join(raw.split()), validate=True)
            b64_path = path.with_suffix(path.suffix + ".base64.decoded")
            b64_path.write_bytes(b64)
            p, v = decode_file_candidates(b64_path, False, max_output)
            public.extend({**x, "source_file": str(path), "base64_unwrapped": True} for x in p)
            valid.extend({**x, "source_file": str(path), "base64_unwrapped": True} for x in v)
        except Exception as exc:
            public.append({"source_file": str(path), "transform": "base64", "status": "fail", "reason": str(exc)[:200]})
    return public, valid


def viewport_from_branch(branch: dict[str, Any]) -> int | None:
    for k in ("width", "innerWidth"):
        v = branch.get(k)
        if isinstance(v, (int, float)):
            return int(round(v))
    doc = branch.get("doc")
    if isinstance(doc, dict):
        for k in ("innerWidth", "width"):
            v = doc.get(k)
            if isinstance(v, (int, float)):
                return int(round(v))
    return None


def node_rect(node: dict[str, Any]) -> dict[str, float] | None:
    if not RECT_KEYS.issubset(node.keys()):
        return None
    try:
        return {k: float(node[k]) for k in ("x", "y", "width", "height")}
    except Exception:
        return None


def text_preview(node: dict[str, Any]) -> str:
    for k in ("text", "textContent", "innerText", "value", "ariaLabel"):
        v = node.get(k)
        if isinstance(v, str) and v.strip():
            return " ".join(v.split())[:160]
    return ""


def build_tree_index(obj: Any, max_nodes: int = 300_000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    def visit(node: Any, json_path: str, h2d_path: str, viewport: int | None) -> None:
        if len(rows) >= max_nodes or not isinstance(node, dict):
            return
        children = node.get("children") if isinstance(node.get("children"), list) else []
        rows.append({"viewport": viewport, "h2d_path_guess": h2d_path, "json_path": json_path, "type": node.get("type"), "tag": node.get("tag"), "rect": node_rect(node), "text_preview": text_preview(node), "children_count": len(children)})
        for i, child in enumerate(children):
            visit(child, f"{json_path}.children[{i}]", f"{h2d_path}.{i}", viewport)
    if isinstance(obj, dict):
        if isinstance(obj.get("frame"), dict):
            visit(obj["frame"], "$.frame", "0", viewport_from_branch(obj))
        for ai, alt in enumerate(obj.get("alternatives") or []):
            if isinstance(alt, dict) and isinstance(alt.get("frame"), dict):
                visit(alt["frame"], f"$.alternatives[{ai}].frame", f"alt{ai}:0", viewport_from_branch(alt))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, dict):
                visit(item.get("frame", item), f"$[{i}]" + (".frame" if "frame" in item else ""), f"{i}.0", viewport_from_branch(item))
    return rows


def discover_schema(obj: Any, tree_index: list[dict[str, Any]], stats: dict[str, Any]) -> dict[str, Any]:
    viewport_roots: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        if isinstance(obj.get("frame"), dict):
            viewport_roots.append({"branch": "default", "width": viewport_from_branch(obj), "frame_path": "$.frame"})
        for i, alt in enumerate(obj.get("alternatives") or []):
            if isinstance(alt, dict) and isinstance(alt.get("frame"), dict):
                viewport_roots.append({"branch": f"alternatives[{i}]", "width": viewport_from_branch(alt), "frame_path": f"$.alternatives[{i}].frame"})
    return {
        "top_level_type": type(obj).__name__,
        "top_level_keys": list(obj.keys())[:80] if isinstance(obj, dict) else [],
        "viewport_roots": viewport_roots,
        "viewport_widths": [r.get("width") for r in viewport_roots],
        "shape": stats,
        "tree_index_count": len(tree_index),
        "sample_nodes": tree_index[:20],
        "asset_count_top_level": len(obj.get("assets", {})) if isinstance(obj, dict) and isinstance(obj.get("assets"), dict) else 0,
        "font_count": len(obj.get("fonts", [])) if isinstance(obj, dict) and isinstance(obj.get("fonts"), list) else 0,
    }


def ext_for_mime(mime: str | None, data: bytes) -> str:
    if mime == "image/svg+xml":
        return ".svg"
    if mime:
        ext = mimetypes.guess_extension(mime.split(";")[0].strip())
        if ext:
            return ".jpg" if ext == ".jpe" else ext
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8"):
        return ".jpg"
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return ".webp"
    if data.lstrip().startswith(b"<svg"):
        return ".svg"
    return ".bin"


def is_font_asset(mime: str | None, data: bytes, source_key: str = "") -> bool:
    m = (mime or "").lower()
    key = (source_key or "").lower()
    return m.startswith("font/") or "woff" in m or key.endswith((".woff", ".woff2", ".ttf", ".otf")) or data.startswith((b"wOFF", b"wOF2", b"OTTO"))


def walk_json(obj: Any, max_visit: int = 200_000) -> Iterable[tuple[str, Any]]:
    stack: list[tuple[str, Any]] = [("$", obj)]
    visited = 0
    while stack and visited < max_visit:
        path, cur = stack.pop()
        visited += 1
        yield path, cur
        if isinstance(cur, dict):
            for k, v in reversed(list(cur.items())):
                if isinstance(v, (dict, list, str)):
                    safe = str(k).replace("/", "~1")[:80]
                    stack.append((f"{path}/{safe}", v))
        elif isinstance(cur, list):
            for i in range(len(cur) - 1, -1, -1):
                v = cur[i]
                if isinstance(v, (dict, list, str)):
                    stack.append((f"{path}/{i}", v))


def decode_data_uri(value: str) -> tuple[str | None, bytes] | None:
    m = DATA_URI_RE.match(value)
    if not m:
        return None
    mime, is_b64, payload = m.groups()
    try:
        data = base64.b64decode(payload) if is_b64 else unquote_to_bytes(payload)
        return mime, data
    except Exception:
        return None


def raster_blankness(data: bytes) -> dict[str, Any]:
    """Return optional raster blankness metadata for PNG/JPEG/WebP/GIF assets."""
    if Image is None or ImageChops is None:
        return {"blank_asset": None, "blankness_warning": "PIL not available"}
    try:
        img = Image.open(io.BytesIO(data))
        width, height = img.size
        result: dict[str, Any] = {
            "raster_width": width,
            "raster_height": height,
            "blank_asset": False,
            "alpha_bbox": None,
            "content_bbox": None,
            "opaque_pixel_ratio": None,
        }
        if "A" in img.getbands():
            alpha = img.getchannel("A")
            bbox = alpha.getbbox()
            result["alpha_bbox"] = list(bbox) if bbox else None
            hist = alpha.histogram()
            opaque = sum(hist[1:])
            result["opaque_pixel_ratio"] = opaque / float(width * height) if width and height else 0
            if bbox is None or result["opaque_pixel_ratio"] < 0.0001:
                result["blank_asset"] = True
        else:
            result["opaque_pixel_ratio"] = 1.0
        rgba = img.convert("RGBA")
        baseline = Image.new("RGBA", rgba.size, rgba.getpixel((0, 0)))
        diff = ImageChops.difference(rgba, baseline)
        bbox = diff.getbbox()
        result["content_bbox"] = list(bbox) if bbox else None
        if bbox is None and result.get("alpha_bbox") is None:
            result["blank_asset"] = True
        return result
    except Exception as exc:  # noqa: BLE001
        return {"blank_asset": None, "blankness_warning": str(exc)[:160]}


def extract_assets(obj: Any, out: Path, max_assets: int = 600, max_asset_bytes: int = 25 * 1024 * 1024) -> dict[str, Any]:
    assets_dir = out / "source" / "extracted_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    assets: list[dict[str, Any]] = []
    external_refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    def add(data: bytes, mime: str | None, path: str, kind: str, source_key: str = "") -> None:
        if len(assets) >= max_assets or not data or len(data) > max_asset_bytes or is_font_asset(mime, data, source_key or path):
            return
        digest = sha256_bytes(data)
        if digest in seen:
            return
        seen.add(digest)
        filename = f"asset_{len(assets)+1:04d}_{digest[:10]}{ext_for_mime(mime, data)}"
        target = assets_dir / filename
        target.write_bytes(data)
        rec = {"json_path": path, "h2d_path": None, "kind": kind, "source_key": source_key, "mime": mime or "application/octet-stream", "file": str(target.relative_to(out)), "bytes": len(data), "sha256": digest, "criticality": "unknown"}
        if ext_for_mime(mime, data).lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            rec.update(raster_blankness(data))
        assets.append(rec)
    for path, value in walk_json(obj):
        if isinstance(value, dict):
            content = value.get("content")
            mime = value.get("mimeType") or value.get("mime")
            if isinstance(content, str) and isinstance(mime, str) and len(content) <= int(max_asset_bytes * 1.45):
                try:
                    data = base64.b64decode(content) if value.get("base64Encoded") is True else content.encode("utf-8")
                    add(data, mime, path, "embedded-content", source_key=path)
                except Exception:
                    pass
        elif isinstance(value, str):
            s = value.strip()
            if s.startswith("http://") or s.startswith("https://"):
                if len(external_refs) < 1000:
                    external_refs.append({"json_path": path, "url": s[:500]})
            elif s.startswith("<svg"):
                add(s.encode("utf-8"), "image/svg+xml", path, "raw-svg")
            elif s.startswith("data:image/") or s.startswith("data:application/octet-stream"):
                decoded = decode_data_uri(s)
                if decoded:
                    mime, data = decoded
                    add(data, mime, path, "data-uri")
    return {"assets": assets, "external_refs": external_refs, "visited_limit": 200000}


def main() -> int:
    ap = argparse.ArgumentParser(description="Safely unpack/decode an H2D source and create v1.5 reports.")
    ap.add_argument("input_h2d", type=Path, help=".h2d file or zip containing .h2d")
    ap.add_argument("--out", type=Path, default=Path("h2d-transfer-output"))
    ap.add_argument("--write-decoded-json", action="store_true", help="Accepted for contract compatibility; decoded JSON is always written compactly")
    ap.add_argument("--extract-assets", action="store_true", help="Extract embedded assets into source/extracted_assets")
    ap.add_argument("--bruteforce-xor", action="store_true", help="Diagnostic only: try all XOR keys for files <=32 MB")
    ap.add_argument("--max-output", type=int, default=DEFAULT_MAX_OUTPUT)
    args = ap.parse_args()

    out = args.out
    source_dir = out / "source"
    reports_dir = out / "reports"
    raw_dir = source_dir / "raw"
    source_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    original_copy = source_dir / "input.original"
    source_copy = source_dir / "input.h2d"
    shutil.copyfile(args.input_h2d, original_copy)
    shutil.copyfile(original_copy, source_copy)
    src = original_copy.read_bytes()
    source_sha = sha256_bytes(src)
    (source_dir / "input.sha256").write_text(source_sha + "  input.original\n", encoding="utf-8")
    intake = {
        "schema_version": "1.5",
        "source_path": str(original_copy.relative_to(out)),
        "sha256": source_sha,
        "size_bytes": len(src),
        "first_bytes_hex": src[:32].hex(),
        "last_bytes_hex": src[-32:].hex() if src else "",
        "sniffed_kind": sniff_kind(src),
        "decoded_kind": "unknown",
        # compatibility fields
        "input_file": str(source_copy.relative_to(out)),
        "input_original": str(original_copy.relative_to(out)),
        "input_original_file": str(original_copy.relative_to(out)),
        "selected_h2d": str(source_copy.relative_to(out)),
        "input_size": len(src),
        "input_sha256": source_sha,
        "first_32_bytes_hex": src[:32].hex(),
        "last_32_bytes_hex": src[-32:].hex() if src else "",
        "copied_byte_identical": sha256_file(original_copy) == source_sha,
    }
    write_json(reports_dir / "source_intake.json", intake)

    archive_manifest: list[dict[str, Any]] = []
    candidate_files = [source_copy]
    if zipfile.is_zipfile(original_copy):
        candidate_files, archive_manifest = safe_zip_members(original_copy, raw_dir)
        candidate_files = [p for p in candidate_files if p.is_file() and (p.suffix.lower() in {".h2d", ".json", ".txt", ".bin"} or p.stat().st_size > 16)]

    public_candidates: list[dict[str, Any]] = []
    valid_candidates: list[dict[str, Any]] = []
    for path in candidate_files:
        public, valid = decode_file_candidates(path, args.bruteforce_xor, args.max_output)
        public_candidates.extend(public)
        valid_candidates.extend({**v, "selected_file": path} for v in valid)
    write_json(reports_dir / "decode_candidates.json", public_candidates)

    if not valid_candidates:
        fail = {"schema_version": "1.5", "status": "fail", "selected_candidate": {}, "decoded_kind": "none", "decoded_bytes": 0, "nodes": 0, "assets": 0, "input_original": str(original_copy.relative_to(out)), "selected_h2d": str(source_copy.relative_to(out)), "input_sha256": source_sha, "archive_manifest": archive_manifest, "candidates": public_candidates, "errors": ["No valid H2D JSON candidate. Stop before HTML transfer."], "warnings": ["No valid H2D JSON candidate. Stop before HTML transfer."]}
        write_json(reports_dir / "h2d_unpack_report.json", fail)
        write_json(reports_dir / "h2d_decode_report.json", fail)
        print("status=fail report=reports/h2d_unpack_report.json")
        return 2

    valid_candidates.sort(key=lambda c: (c["score"], c["decoded_bytes"]), reverse=True)
    best = valid_candidates[0]
    selected_file = Path(best["selected_file"])
    if selected_file.resolve() != source_copy.resolve():
        shutil.copyfile(selected_file, source_copy)
    decoded_json = best["json"]
    decoded_bytes = best["decoded"]
    decoded_path = source_dir / "h2d_decoded.json"
    decoded_path.write_text(json.dumps(decoded_json, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tree_index = build_tree_index(decoded_json)
    tree_index_path = source_dir / "h2d_tree_index.json"
    write_json(tree_index_path, tree_index, pretty=False)
    schema = discover_schema(decoded_json, tree_index, best["shape"])
    write_json(reports_dir / "schema_discovery.json", schema)
    asset_inventory_raw = extract_assets(decoded_json, out) if args.extract_assets else {"assets": [], "external_refs": [], "visited_limit": 0}
    normalized_assets = []
    for i, a in enumerate(asset_inventory_raw.get("assets", []), 1):
        normalized_assets.append({
            **a,
            "asset_id": a.get("asset_id") or f"raw-asset-{i:04d}",
            "kind": "svg" if a.get("mime") == "image/svg+xml" else ("image" if str(a.get("mime", "")).startswith("image/") else a.get("kind", "unknown")),
            "source": a.get("file") or a.get("source_key") or a.get("json_path") or "unknown",
            "h2d_path": a.get("h2d_path"),
            "blank_alpha": bool(a.get("blank_asset", False)) if a.get("blank_asset") is not None else None,
        })
    asset_inventory = {"schema_version": "1.5", "assets": normalized_assets, "external_refs": asset_inventory_raw.get("external_refs", []), "visited_limit": asset_inventory_raw.get("visited_limit", 0)}
    write_json(reports_dir / "raw_asset_inventory.json", asset_inventory)

    selected_public = {k: v for k, v in best.items() if k not in {"json", "decoded", "selected_file"}}
    status = "partial" if len(valid_candidates) > 1 and valid_candidates[1]["score"] == best["score"] and valid_candidates[1].get("decoded_sha256") != best.get("decoded_sha256") else "ok"
    unpack_report = {
        "schema_version": "1.5",
        "status": status,
        "decoded_kind": "utf8-json",
        "nodes": len(tree_index),
        "assets": len(asset_inventory.get("assets", [])),
        "source_unpack_verdict": "pass" if len(tree_index) > 0 else "partial",
        "input_original": str(original_copy.relative_to(out)),
        "selected_h2d": str(source_copy.relative_to(out)),
        "input_sha256": source_sha,
        "input_size": len(src),
        "sniffed_kind": intake["sniffed_kind"],
        "detected_container": "zip" if archive_manifest else "single-file",
        "decoded_kind": f"{best['transform']}->{best['codec']}->utf8-json",
        "selected_candidate": selected_public,
        "decode_chain": [{"step": best["transform"], "xor_key": best.get("xor_key")}, {"step": best["codec"], "wbits": best.get("wbits")}, {"step": "utf8-json"}],
        "decoded_json_file": str(decoded_path.relative_to(out)),
        "decoded_json_sha256": sha256_file(decoded_path),
        "decoded_stream_sha256": sha256_bytes(decoded_bytes),
        "decoded_bytes": best["decoded_bytes"],
        "decoded_json_size": decoded_path.stat().st_size,
        "h2d_tree_index_file": str(tree_index_path.relative_to(out)),
        "node_count_indexed": len(tree_index),
        "viewport_widths": schema.get("viewport_widths", []),
        "raw_assets_found": len(asset_inventory.get("assets", [])),
        "external_refs_found": len(asset_inventory.get("external_refs", [])),
        "archive_manifest": archive_manifest,
        "warnings": [] if status == "ok" else ["Multiple decode candidates have the same score. Manual review required."],
    }
    write_json(reports_dir / "h2d_unpack_report.json", unpack_report)
    write_json(reports_dir / "h2d_decode_report.json", {"status": status, "source": "compatibility_alias_of_h2d_unpack_report", "xor_key": best.get("xor_key"), "wbits": best.get("wbits"), "codec": best.get("codec"), "decoded_bytes": best.get("decoded_bytes"), "h2d_unpack_report": "reports/h2d_unpack_report.json"})
    manifest_paths = [original_copy, source_copy, source_dir / "input.sha256", decoded_path, tree_index_path, reports_dir / "source_intake.json", reports_dir / "decode_candidates.json", reports_dir / "schema_discovery.json", reports_dir / "raw_asset_inventory.json", reports_dir / "h2d_unpack_report.json", reports_dir / "h2d_decode_report.json"]
    manifest_paths.extend((out / a["file"]) for a in asset_inventory.get("assets", []))
    write_json(reports_dir / "source_manifest.json", {"schema_version": "1.5", "files": [{"path": str(p.relative_to(out)), "file": str(p.relative_to(out)), "size_bytes": p.stat().st_size, "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in manifest_paths if p.exists()], "archive_manifest": archive_manifest})
    print(f"status={status} transform={best['transform']} codec={best['codec']} decoded={best['decoded_bytes']}B nodes={len(tree_index)} assets={len(asset_inventory.get('assets', []))}")
    return 0 if status == "ok" else 3


if __name__ == "__main__":
    raise SystemExit(main())
