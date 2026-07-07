#!/usr/bin/env python3
"""Audit bitmap files for visible pixels (v1.5 helper).

Usage:
  python scripts/asset_bitmap_audit.py dist/assets --out reports/asset_bitmap_audit.json
  python scripts/asset_bitmap_audit.py dist/assets --fail-on-any-blank

Checks whether image files are blank/fully transparent and records dimensions,
alpha/RGB bbox and non-transparent pixel ratio. This helps catch extracted but
empty canvas images. Default exit code is 0 because decorative transparent files
may be valid; use --fail-on-any-blank only for strict critical-asset subsets.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any
from PIL import Image

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def bbox_to_list(b):
    return None if b is None else [int(x) for x in b]

def audit_image(path: Path) -> dict[str, Any]:
    rec: dict[str, Any] = {'file': str(path), 'bytes': path.stat().st_size, 'sha256': sha256_file(path)}
    try:
        im = Image.open(path)
        rec['format'] = im.format
        rec['width'], rec['height'] = im.size
        rgba = im.convert('RGBA')
        alpha = rgba.getchannel('A')
        alpha_bbox = alpha.getbbox()
        rgb_bbox = rgba.convert('RGB').getbbox()
        non_transparent = sum(1 for v in alpha.getdata() if v > 0)
        total = rgba.width * rgba.height
        rec.update({
            'alpha_bbox': bbox_to_list(alpha_bbox),
            'rgb_bbox': bbox_to_list(rgb_bbox),
            'non_transparent_pixels': non_transparent,
            'total_pixels': total,
            'non_transparent_ratio': non_transparent / total if total else 0,
            'blank_alpha': alpha_bbox is None,
            'blank_rgb': rgb_bbox is None,
            'result': 'fail' if alpha_bbox is None or non_transparent == 0 else 'pass'
        })
    except Exception as exc:
        rec.update({'result': 'fail', 'error': str(exc)[:300]})
    return rec

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+', type=Path)
    ap.add_argument('--out', type=Path, default=Path('reports/asset_bitmap_audit.json'))
    ap.add_argument('--fail-on-any-blank', action='store_true', help='Return exit code 1 if any inspected bitmap is blank/transparent')
    args = ap.parse_args()
    files: list[Path] = []
    for p in args.paths:
        if p.is_dir():
            files.extend(x for x in p.rglob('*') if x.suffix.lower() in IMAGE_EXTS)
        elif p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            files.append(p)
    results = [audit_image(p) for p in sorted(set(files))]
    failures = [r for r in results if r.get('result') != 'pass']
    out = {'files': results, 'failures': failures, 'result': 'manual-review' if failures else 'pass'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"files={len(results)} failures={len(out['failures'])} result={out['result']} report={args.out}")
    return 1 if args.fail_on_any_blank and failures else 0

if __name__ == '__main__':
    raise SystemExit(main())
