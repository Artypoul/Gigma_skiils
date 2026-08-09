#!/usr/bin/env python3
"""Finalize visual and dynamic reference evidence under one immutable donor identity."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from evidence_integrity import EvidenceError, load_json, sha256_file


ROOT = Path(__file__).resolve().parents[1]


def relative_artifacts(base: Path, entries: list[dict]) -> list[dict]:
    result = []
    for entry in entries:
        path = (base / entry["path"]).resolve()
        path.relative_to(base.resolve())
        if not path.is_file() or sha256_file(path) != entry.get("sha256"):
            raise EvidenceError(f"reference artifact is missing or changed: {entry.get('path')}")
        result.append({**entry, "path": path.relative_to(base).as_posix()})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h2d", type=Path, required=True)
    parser.add_argument("--donor", type=Path, required=True, help="Pinned local runnable donor entry; live URLs are rejected")
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--profiles", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--classification", type=Path)
    parser.add_argument("--dynamic-manifest", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    command = [
        "node", str(ROOT / "scripts" / "freeze_visual_reference.js"),
        "--donor", str(args.donor), "--matrix", str(args.matrix),
        "--profiles", str(args.profiles), "--out-dir", str(args.out),
    ]
    if args.project_root:
        command += ["--project-root", str(args.project_root)]
    subprocess.run(command, check=True)
    visual_path = args.out / "visual_reference_manifest.json"
    visual = load_json(visual_path)
    if visual.get("result") != "pass":
        raise EvidenceError("visual reference capture is non-pass")
    behavior_required = liveness_required = False
    classification = {"behavior_required": False, "liveness_required": False, "coverage_complete": True}
    if args.classification:
        classification = load_json(args.classification)
        behavior_required = bool(classification.get("behavior_required"))
        liveness_required = bool(classification.get("liveness_required"))
        if classification.get("coverage_complete") is not True or classification.get("result") != "pass":
            raise EvidenceError("reference classification is incomplete or non-pass")
    dynamic = {"donor_identity": None, "artifacts": []}
    if behavior_required or liveness_required:
        if not args.dynamic_manifest:
            raise EvidenceError("interactive/dynamic classification requires --dynamic-manifest")
        dynamic = load_json(args.dynamic_manifest)
        if dynamic.get("result") != "pass" or dynamic.get("coverage_complete") is not True:
            raise EvidenceError("dynamic reference manifest is incomplete or non-pass")
        if dynamic.get("donor_identity") != visual.get("donor_identity"):
            raise EvidenceError("visual and dynamic phases used different donor identities")
        if sorted(dynamic.get("matrix_keys") or []) != sorted(visual.get("matrix_keys") or []):
            raise EvidenceError("dynamic reference matrix differs from visual matrix")
    artifacts = relative_artifacts(args.out, visual.get("artifacts") or [])
    artifacts.append({"path": visual_path.relative_to(args.out).as_posix(), "sha256": sha256_file(visual_path), "kind": "visual-manifest"})
    if args.classification:
        destination = args.out / "reference_classification.json"
        destination.write_text(json.dumps(classification, indent=2, ensure_ascii=False), encoding="utf-8")
        artifacts.append({"path": destination.relative_to(args.out).as_posix(), "sha256": sha256_file(destination), "kind": "classification"})
    if args.dynamic_manifest:
        dynamic_path = args.dynamic_manifest.resolve()
        dynamic_out = args.out / "dynamic"
        dynamic_out.mkdir(parents=True, exist_ok=True)
        for item in dynamic.get("artifacts") or []:
            source = (dynamic_path.parent / item["path"]).resolve()
            if not source.is_file() or sha256_file(source) != item.get("sha256"):
                raise EvidenceError(f"dynamic artifact is missing or changed: {item.get('path')}")
            target = dynamic_out / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            artifacts.append({"path": target.relative_to(args.out).as_posix(), "sha256": sha256_file(target), "kind": item.get("kind", "dynamic-artifact")})
        manifest_target = dynamic_out / "dynamic_reference_manifest.json"
        shutil.copyfile(dynamic_path, manifest_target)
        artifacts.append({"path": manifest_target.relative_to(args.out).as_posix(), "sha256": sha256_file(manifest_target), "kind": "dynamic-manifest"})
    source_sha = sha256_file(args.h2d.resolve())
    bundle = {
        "schema_version": "2.0", "result": "pass", "coverage_complete": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": source_sha, "donor_identity": visual["donor_identity"],
        "environment_sha256": visual.get("environment_sha256"),
        "matrix_keys": sorted(visual["matrix_keys"]),
        "visual": {"donor_identity": visual["donor_identity"], "manifest_sha256": sha256_file(visual_path)},
        "dynamic": {"donor_identity": dynamic.get("donor_identity"), "required": behavior_required or liveness_required},
        "classification": classification,
        "artifacts": artifacts,
    }
    out = args.out / "reference_bundle.json"
    out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"result=pass matrix={len(bundle['matrix_keys'])} out={out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EvidenceError, subprocess.CalledProcessError) as error:
        print(f"reference-freeze blocked: {error}", file=sys.stderr)
        raise SystemExit(2)
