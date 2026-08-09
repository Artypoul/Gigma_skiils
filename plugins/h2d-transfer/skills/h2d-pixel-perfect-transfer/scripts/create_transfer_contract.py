#!/usr/bin/env python3
"""Create an immutable H2D transfer contract from freshly decoded source bytes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from evidence_integrity import EvidenceError, candidate_closure, command_executable_records, load_json, sha256_file, verify_contract


ROOT = Path(__file__).resolve().parents[1]


def rel(base: Path, target: Path, label: str) -> str:
    try:
        return target.resolve().relative_to(base.resolve()).as_posix()
    except ValueError as exc:
        raise EvidenceError(f"{label} must be inside contract directory {base}: {target}") from exc


def parse_profiles(path: Path) -> list[dict]:
    profiles = load_json(path)
    if not isinstance(profiles, list) or not profiles:
        raise EvidenceError("profiles must be a non-empty JSON array")
    ids = [row.get("id") for row in profiles if isinstance(row, dict)]
    if len(ids) != len(profiles) or len(ids) != len(set(ids)) or any(not isinstance(value, str) or not value for value in ids):
        raise EvidenceError("profiles need unique stable ids")
    required = {"headless", "device_scale_factor", "is_mobile", "has_touch", "locale", "timezone", "reduced_motion"}
    for profile in profiles:
        missing = sorted(required - set(profile))
        if missing:
            raise EvidenceError(f"profile {profile.get('id')} misses {missing}")
    return profiles


def responsive_matrix(widths: list[int], heights: dict[str, int], breakpoints: list[int]) -> list[dict]:
    decoded = sorted(set(int(width) for width in widths if isinstance(width, int) and width > 0))
    if not decoded:
        raise EvidenceError("fresh H2D decode contains no viewport widths")
    rows: dict[int, dict] = {}
    default_height = max(heights.values()) if heights else 1440
    for width in decoded:
        rows[width] = {"width": width, "height": int(heights.get(str(width), default_height)), "kind": "decoded"}
    boundaries = sorted(set(int(value) for value in breakpoints if int(value) > 1))
    if len(decoded) > 1:
        if not boundaries:
            raise EvidenceError("multiple decoded widths require a complete pinned --breakpoints list")
        uncovered = [(left, right) for left, right in zip(decoded, decoded[1:]) if right - left > 2 and not any(left < point <= right for point in boundaries)]
        if uncovered:
            raise EvidenceError(f"breakpoints do not cover decoded intervals: {uncovered}")
    for point in boundaries:
        for width in (point - 1, point, point + 1):
            rows.setdefault(width, {"width": width, "height": int(heights.get(str(width), default_height)), "kind": "breakpoint-boundary"})
    for left, right in zip(decoded, decoded[1:]):
        if right - left > 2:
            width = (left + right) // 2
            rows.setdefault(width, {"width": width, "height": int(heights.get(str(width), default_height)), "kind": "interval-probe"})
    return [rows[key] for key in sorted(rows)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h2d", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--candidate-include", action="append", required=True)
    parser.add_argument("--candidate-mode", choices=["entry", "managed-url"], default="entry")
    parser.add_argument("--candidate-lifecycle", type=Path)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--height-map", type=Path, required=True)
    parser.add_argument("--breakpoints", default="", help="Comma-separated donor breakpoint boundaries; mandatory and interval-complete when H2D has multiple decoded widths")
    parser.add_argument("--reference-bundle", type=Path, required=True)
    parser.add_argument("--sidecar", action="append", default=[], help="role=path")
    parser.add_argument("--approval", action="append", type=Path, default=[])
    parser.add_argument("--current-command", action="append", default=[], help="JSON array command; repeated, pinned in execution order")
    parser.add_argument("--expected-report", action="append", required=True, help="Path relative to transfer output; repeated")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    workspace = args.workspace_root.resolve()
    candidate_root = args.candidate_root.resolve()
    candidate_root.relative_to(workspace)
    contract_dir = args.out.resolve().parent
    contract_dir.mkdir(parents=True, exist_ok=True)
    source_output = contract_dir / "fresh_decode"
    decoder = ROOT / "scripts" / "h2d_unpack_source.py"
    subprocess.run([sys.executable, str(decoder), str(args.h2d.resolve()), "--out", str(source_output)], check=True)
    unpack = load_json(source_output / "reports" / "h2d_unpack_report.json")
    if unpack.get("status") != "ok" or unpack.get("source_unpack_verdict") != "pass":
        raise EvidenceError("fresh H2D decode is not an unambiguous pass")
    source_path = source_output / "source" / "input.h2d"
    decoded_paths = [source_output / "source" / "h2d_decoded.json", source_output / "source" / "h2d_tree_index.json"]
    heights = load_json(args.height_map)
    if not isinstance(heights, dict):
        raise EvidenceError("height-map must be a JSON object keyed by viewport width")
    profiles = parse_profiles(args.profiles)
    breakpoints = [int(value) for value in args.breakpoints.split(",") if value.strip()]
    matrix = responsive_matrix(unpack.get("viewport_widths") or [], heights, breakpoints)
    closure = candidate_closure(candidate_root, args.candidate_include, contract_dir.parent)
    bundle_path = args.reference_bundle.resolve()
    bundle = load_json(bundle_path)
    expected_keys = sorted(f"{row['width']}x{row['height']}@{profile['id']}" for row in matrix for profile in profiles)
    if bundle.get("source_sha256") != sha256_file(source_path):
        raise EvidenceError("reference bundle is bound to different H2D bytes")
    if sorted(bundle.get("matrix_keys") or []) != expected_keys:
        raise EvidenceError("reference bundle does not cover derived responsive/profile matrix")
    sidecars = []
    for value in args.sidecar:
        role, separator, raw_path = value.partition("=")
        if not separator or not role or not raw_path:
            raise EvidenceError("--sidecar must use role=path")
        sidecar_path = Path(raw_path).resolve()
        sidecars.append({"role": role, "path": rel(contract_dir, sidecar_path, f"sidecar {role}"), "sha256": sha256_file(sidecar_path)})
    approvals = [load_json(path.resolve()) for path in args.approval]
    commands = []
    for raw in args.current_command:
        command = json.loads(raw)
        if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
            raise EvidenceError("--current-command must be a non-empty JSON string array")
        commands.append(command)
    if not commands:
        raise EvidenceError("at least one --current-command is required")
    lifecycle = load_json(args.candidate_lifecycle.resolve()) if args.candidate_lifecycle else None
    if args.candidate_mode == "managed-url" and not lifecycle:
        raise EvidenceError("managed-url candidate requires --candidate-lifecycle")
    all_commands = list(commands)
    for key in ("build", "start", "teardown"):
        if lifecycle and lifecycle.get(key):
            all_commands.append(lifecycle[key])
    contract = {
        "schema_version": "2.0", "created_at": datetime.now(timezone.utc).isoformat(),
        "workspace_root": str(workspace),
        "source": {"path": rel(contract_dir, source_path, "fresh source"), "sha256": sha256_file(source_path)},
        "decoder": {"path": "builtin:scripts/h2d_unpack_source.py", "sha256": sha256_file(decoder)},
        "decoded_artifacts": [{"path": rel(contract_dir, path, "decoded artifact"), "sha256": sha256_file(path)} for path in decoded_paths],
        "responsive_matrix": matrix, "browser_profiles": profiles,
        "candidate": {
            "mode": args.candidate_mode,
            "project_root": candidate_root.relative_to(workspace).as_posix() or ".",
            "include": args.candidate_include,
            "closure_sha256": closure["digest"],
            "lifecycle": lifecycle,
        },
        "classification": bundle.get("classification") or {"behavior_required": False, "liveness_required": False, "coverage_complete": True},
        "reference_bundle": {"path": rel(contract_dir, bundle_path, "reference bundle"), "sha256": sha256_file(bundle_path)},
        "sidecars": sidecars, "approvals": approvals, "current_commands": commands,
        "command_executables": command_executable_records(all_commands),
        "expected_reports": args.expected_report,
        "matrix_keys": expected_keys,
    }
    args.out.write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")
    verify_contract(args.out, contract_dir.parent)
    print(f"result=pass viewports={len(matrix)} profiles={len(profiles)} matrix={len(expected_keys)} out={args.out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EvidenceError, subprocess.CalledProcessError, ValueError) as error:
        print(f"contract blocked: {error}", file=sys.stderr)
        raise SystemExit(2)
