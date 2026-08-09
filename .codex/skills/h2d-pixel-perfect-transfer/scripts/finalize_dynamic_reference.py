#!/usr/bin/env python3
"""Build the only accepted dynamic-reference manifest from explicit hashed artifacts."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from evidence_integrity import EvidenceError, canonical_json_sha256, required_dynamic_roles, sha256_file


SCRIPT = Path(__file__).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--classification", type=Path, required=True)
    parser.add_argument("--artifact", action="append", default=[], help="kind@matrix-key=path; use kind@*=path for an aggregate artifact")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    classification = json.loads(args.classification.read_text(encoding="utf-8"))
    if classification.get("result") != "pass" or classification.get("coverage_complete") is not True:
        raise EvidenceError("dynamic reference requires a complete generated classification")
    matrix = sorted(classification.get("matrix_keys") or [])
    if not matrix:
        raise EvidenceError("classification matrix is empty")
    artifacts = []
    for raw in args.artifact:
        spec, separator, raw_path = raw.partition("=")
        kind, marker, matrix_key = spec.partition("@")
        if not separator or not marker or not kind or not matrix_key or not raw_path:
            raise EvidenceError("--artifact must use kind@matrix-key=path")
        keys = matrix if matrix_key == "*" else [matrix_key]
        if any(key not in matrix for key in keys):
            raise EvidenceError(f"dynamic artifact uses an unknown matrix key: {matrix_key}")
        source = Path(raw_path).resolve()
        if not source.is_file() or source.stat().st_size == 0:
            raise EvidenceError(f"dynamic artifact is missing or empty: {source}")
        artifacts.append({"kind": kind, "path": source.name, "sha256": sha256_file(source), "matrix_keys": keys, "source_path": str(source)})
    required = required_dynamic_roles(classification)
    for role in required:
        covered = {key for item in artifacts if item["kind"] == role for key in item["matrix_keys"]}
        if covered != set(matrix):
            raise EvidenceError(f"dynamic role {role} does not cover the complete matrix")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # The portable manifest paths are relative to the manifest. Copying remains
    # the caller's explicit responsibility; freeze_reference_bundle verifies bytes.
    portable = []
    for item in artifacts:
        source = Path(item.pop("source_path"))
        target = args.out.parent / item["path"]
        if source != target.resolve():
            raise EvidenceError("dynamic artifacts must be colocated with the output manifest before finalization")
        portable.append(item)
    report = {
        "schema_version": "2.0", "result": "pass", "coverage_complete": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generator_sha256": sha256_file(SCRIPT),
        "classification_sha256": canonical_json_sha256(classification),
        "donor_identity": classification["donor_identity"], "matrix_keys": matrix,
        "required_roles": sorted(required), "artifacts": portable,
    }
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"result=pass roles={len(required)} artifacts={len(portable)} out={args.out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceError as error:
        print(f"dynamic reference blocked: {error}")
        raise SystemExit(2)
