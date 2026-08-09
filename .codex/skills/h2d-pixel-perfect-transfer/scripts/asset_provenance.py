#!/usr/bin/env python3
"""Record where every shipped asset came from and what it costs to ship it.

A donor snapshot carries the donor's own material: logos, showreels, portfolio
imagery. Reproducing geometry is the transfer; republishing someone else's brand
or a multi-megabyte video is a decision that belongs to the owner. This script
matches candidate assets against the extracted h2d inventory by content hash,
then fails the gate while any asset that needs a decision has none.

Brand ownership cannot be judged from bytes, so it is never guessed: for any
asset traced back to the donor the agent must record `third_party_brand` in the
decisions file. The script's job is to make that judgement impossible to skip.

  python scripts/asset_provenance.py \
    --assets public/hero-orb-1440.png public/hero-showreel.mp4 \
    --raw-asset-inventory h2d-transfer-output/reports/raw_asset_inventory.json \
    --decisions h2d-transfer-output/reports/asset_decisions.json \
    --out h2d-transfer-output/reports/asset_provenance.json
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLD = 1024 * 1024
DECISION_VALUES = {'approved-as-is', 'approved-as-placeholder', 'replace-before-publish', 'removed', 'pending'}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files(entries: list[str]) -> tuple[list[Path], list[str]]:
    """Resolve assets and report arguments that matched nothing.

    A typo in a path or glob must never silently produce an empty asset list:
    the runner treats this report as the mandatory provenance proof, so an
    unmatched argument would turn a skipped check into a green gate.
    """
    files: list[Path] = []
    unmatched: list[str] = []
    for entry in entries:
        path = Path(entry)
        if path.is_dir():
            found = sorted(p for p in path.rglob('*') if p.is_file())
        elif path.is_file():
            found = [path]
        else:
            # Allow globs like public/hero-*.png
            found = sorted(p for p in Path().glob(entry) if p.is_file())
        if not found:
            unmatched.append(entry)
        files.extend(found)
    unique: dict[Path, None] = {}
    for f in files:
        unique.setdefault(f.resolve(), None)
    return list(unique), unmatched


def load_inventory(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    by_hash: dict[str, dict[str, Any]] = {}
    for asset in data.get('assets') or []:
        digest = asset.get('sha256')
        if isinstance(digest, str) and digest:
            by_hash.setdefault(digest.lower(), asset)
    return by_hash


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--assets', nargs='+', required=True, help='Files, directories or globs shipped by the candidate')
    ap.add_argument('--raw-asset-inventory', type=Path)
    ap.add_argument('--decisions', type=Path, help='JSON map: {"<path>": {"third_party_brand": bool, "owner_decision": "...", ...}}')
    ap.add_argument('--threshold-bytes', type=int, default=DEFAULT_THRESHOLD)
    ap.add_argument('--allow-empty', action='store_true', help='The candidate genuinely ships no assets; without this an empty result is a failure, not a pass.')
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()

    inventory = load_inventory(args.raw_asset_inventory)
    decisions = json.loads(args.decisions.read_text(encoding='utf-8')) if args.decisions and args.decisions.exists() else {}
    # Decisions may be keyed by any spelling of the same path.
    decisions = {str(k).replace('\\', '/').lstrip('./'): v for k, v in decisions.items()}

    assets: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []
    cwd = Path.cwd()

    files, unmatched = collect_files(args.assets)
    for entry in unmatched:
        issues.append({'path': entry, 'issue': 'asset argument matched no files: fix the path or glob instead of shipping an unchecked asset'})
    if not files and not args.allow_empty:
        issues.append({'path': '(none)', 'issue': 'no assets resolved; pass --allow-empty only when the candidate genuinely ships no assets'})

    for path in files:
        try:
            rel = path.relative_to(cwd)
        except ValueError:
            rel = path
        key = str(rel).replace('\\', '/')
        digest = sha256_file(path)
        size = path.stat().st_size
        decision = decisions.get(key) or decisions.get(path.name) or {}

        matched = inventory.get(digest)
        if matched:
            origin_kind = 'h2d-extracted'
            origin = f"{matched.get('asset_id') or 'h2d asset'} ({matched.get('file') or matched.get('source') or 'extracted'})"
        elif decision.get('origin_kind'):
            origin_kind = decision['origin_kind']
            origin = decision.get('origin') or 'declared by agent'
        else:
            origin_kind = 'unknown'
            origin = 'not matched against the h2d inventory'

        entry: dict[str, Any] = {
            'path': key,
            'bytes': size,
            'sha256': digest,
            'origin': origin,
            'origin_kind': origin_kind,
        }
        for field in ('decision_note', 'license_note', 'owner_decision'):
            if decision.get(field):
                entry[field] = decision[field]

        donor_derived = origin_kind in {'h2d-extracted', 'donor-cdn'}
        brand = decision.get('third_party_brand')
        if brand is None:
            if donor_derived:
                issues.append({'path': key, 'issue': 'third_party_brand not declared for a donor-derived asset'})
                entry['third_party_brand'] = False
                entry.setdefault('owner_decision', 'pending')
            else:
                entry['third_party_brand'] = False
        else:
            entry['third_party_brand'] = bool(brand)

        needs_decision = entry['third_party_brand'] or size >= args.threshold_bytes
        if needs_decision:
            chosen = entry.get('owner_decision')
            if chosen not in DECISION_VALUES or chosen == 'pending':
                reason = 'third-party brand content' if entry['third_party_brand'] else f'{size} bytes exceeds the {args.threshold_bytes} byte threshold'
                issues.append({'path': key, 'issue': f'owner decision required ({reason})'})
                entry['owner_decision'] = chosen if chosen in DECISION_VALUES else 'pending'
            elif chosen == 'removed':
                # The file was just hashed from the shipped set, so "removed"
                # describes an action nobody took.
                issues.append({'path': key, 'issue': 'owner_decision is "removed" but the asset is still present in the shipped set'})
        if origin_kind == 'unknown':
            issues.append({'path': key, 'issue': 'origin unknown: not in the h2d inventory and not declared'})

        assets.append(entry)

    result = 'pass' if not issues else 'needs-decision'
    report = {
        'result': result,
        'size_threshold_bytes': args.threshold_bytes,
        'assets': assets,
        'issues': issues,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    total = sum(a['bytes'] for a in assets)
    print(f'result={result} assets={len(assets)} total_bytes={total} issues={len(issues)} out={args.out}')
    return 0 if result == 'pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
