#!/usr/bin/env python3
"""Derive seed or final reference viewports from fresh H2D bytes and generated donor breakpoints."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from create_transfer_contract import responsive_matrix
from evidence_integrity import EvidenceError, load_json, sha256_file


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h2d", type=Path, required=True)
    parser.add_argument("--height-map", type=Path, required=True)
    parser.add_argument("--classification", type=Path, help="Complete output from classify_reference.js; omit for the decoded-width seed matrix")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    h2d = args.h2d.resolve()
    heights = load_json(args.height_map.resolve())
    if not isinstance(heights, dict) or any(not isinstance(value, int) or value <= 0 for value in heights.values()):
        raise EvidenceError("height-map must contain positive integer heights")
    breakpoints: list[int] = []
    if args.classification:
        classification = load_json(args.classification.resolve())
        if classification.get("result") != "pass" or classification.get("coverage_complete") is not True:
            raise EvidenceError("final matrix requires a complete generated classification")
        if classification.get("generator_sha256") != sha256_file(ROOT / "scripts" / "classify_reference.js"):
            raise EvidenceError("classification was not produced by the bundled classifier")
        if classification.get("source_sha256") != sha256_file(h2d):
            raise EvidenceError("classification is bound to different H2D bytes")
        breakpoints = classification.get("breakpoints") or []
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in breakpoints):
            raise EvidenceError("classification breakpoints are invalid")
    with tempfile.TemporaryDirectory(prefix="h2d-matrix-") as temp:
        decode = Path(temp) / "decode"
        subprocess.run([sys.executable, str(ROOT / "scripts" / "h2d_unpack_source.py"), str(h2d), "--out", str(decode)], check=True)
        report = load_json(decode / "reports" / "h2d_unpack_report.json")
        if report.get("status") != "ok" or report.get("source_unpack_verdict") != "pass":
            raise EvidenceError("fresh H2D decode is not an unambiguous pass")
        matrix = responsive_matrix(report.get("viewport_widths") or [], heights, breakpoints)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(matrix, indent=2, ensure_ascii=False), encoding="utf-8")
    phase = "final" if args.classification else "seed"
    print(f"result=pass phase={phase} viewports={len(matrix)} out={args.out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EvidenceError, subprocess.CalledProcessError, ValueError) as error:
        print(f"reference matrix blocked: {error}", file=sys.stderr)
        raise SystemExit(2)
