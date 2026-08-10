#!/usr/bin/env python3
"""Extract viewport-scoped rect targets from source/h2d_tree_index.json."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any


def load_root_map(value: str) -> dict[int, str]:
    p = Path(value)
    raw = p.read_text(encoding='utf-8') if p.exists() else value
    obj = json.loads(raw)
    return {int(k): str(v) for k, v in obj.items()}


def path_matches(path: str, root: str) -> bool:
    return path == root or path.startswith(root + '.')


def is_ancestor(path: str, root: str) -> bool:
    return bool(path) and root.startswith(path + '.')


def parent_path(path: str) -> str | None:
    return path.rsplit('.', 1)[0] if '.' in path else None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree-index', type=Path, required=True)
    ap.add_argument('--scope', required=True)
    ap.add_argument('--root-map', required=True, help='JSON object or path, e.g. {"390":"0.0.0.2.0"}')
    ap.add_argument('--coordinate-space', default='page', choices=['page','branch-local','component-local'])
    ap.add_argument('--without-ancestors', action='store_true', help='Diagnostic only: omit the viewport/page/container ancestor chain. Final gates reject this mode.')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    rows: list[dict[str, Any]] = json.loads(args.tree_index.read_text(encoding='utf-8'))
    root_map = load_root_map(args.root_map)
    viewports = []
    total = 0
    for viewport, root in sorted(root_map.items()):
        targets = []
        for row in rows:
            path = str(row.get('h2d_path_guess') or '')
            rect = row.get('rect')
            row_vp = row.get('viewport')
            if row_vp is not None and int(row_vp) != viewport:
                continue
            descendant = path_matches(path, root)
            ancestor = is_ancestor(path, root)
            if not rect or not (descendant or (ancestor and not args.without_ancestors)):
                continue
            relation = 'scope-root' if path == root else ('scope-ancestor' if ancestor else 'scope-descendant')
            target = {
                'key': f'{viewport}::{path}',
                'data_h2d_path': path,
                'json_path': row.get('json_path'),
                'type': row.get('type'),
                'tag': row.get('tag'),
                'rect': {k: float(rect[k]) for k in ('x','y','width','height')},
                'text_preview': row.get('text_preview') or '',
                'parent_path': parent_path(path),
                'relation_to_scope': relation,
            }
            # Typography and container constraints are part of the target, not
            # decoration: matching a rect with the wrong font or a compensating
            # spacer is exactly the failure these fields make visible.
            for key in ('text_style', 'rendered_font', 'box_style'):
                if row.get(key):
                    target[key] = row[key]
            targets.append(target)
        targets.sort(key=lambda item: (item['data_h2d_path'].count('.'), item['data_h2d_path']))
        total += len(targets)
        viewports.append({
            'viewport': viewport,
            'root_path': root,
            'targets': targets,
            'target_count': len(targets),
            'ancestor_target_count': sum(1 for target in targets if target['relation_to_scope'] == 'scope-ancestor'),
            'layout_target_count': sum(1 for target in targets if target.get('box_style')),
        })
    out = {
        'scope': args.scope,
        'coordinate_space': args.coordinate_space,
        'viewport_key_format': '<viewport>::<data-h2d-path>',
        'coverage_mode': 'scope-only' if args.without_ancestors else 'complete-ancestor-chain',
        'includes_ancestors': not args.without_ancestors,
        'root_map': {str(key): value for key, value in sorted(root_map.items())},
        'source_tree_sha256': sha256_file(args.tree_index),
        'generator_sha256': sha256_file(Path(__file__)),
        'viewports': viewports,
        'total_targets': total,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'scope={args.scope} viewports={len(viewports)} targets={total} out={args.out}')
    return 0 if total else 2

if __name__ == '__main__':
    raise SystemExit(main())
